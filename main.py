import os
import time
import gc
import copy
from datetime import datetime
from flask import (
    Flask, request, make_response, jsonify, abort, Response, send_file
)
from flask_cors import CORS

from models.app_setting import AppSetting
from models.file_access import FileAccess
from models.dir_access import DirAccess
from models.speech_to_text import SpeechToText
from models.file_list import FileList


# 初期設定
PATH_CONFIG_FILE = "./config/appconfig.json"
app = Flask(__name__)
AppSetting.set_config(app, PATH_CONFIG_FILE)
# サーバーを跨いでのリクエストを許可
CORS(app)


# postされた音声ファイルを保存
@app.route("/saveFile", methods=["POST"])
def save_file() -> Response:
    # リクエスト受取り
    audio_file = request.files["audioFile"]
    saving_file_name = request.form["savingFileName"]
    # 変数宣言
    dir_path_audio = ""
    dir_path_csv = ""
    dir_name_today = saving_file_name.split("_")[0]
    list_mime_type = []
    list_audio_file_name = []
    file_list = None
    file_access = FileAccess(PATH_CONFIG_FILE)

    # 設定ファイルを読み込み、保存を許可するファイルの種類を取得
    file_access.read_json_file()
    list_mime_type = file_access.json_data["mimeType"]["audio"]

    # アップロードされた音声ファイルの種類が不正である場合、エラーを発生
    if audio_file.mimetype not in list_mime_type:
        abort(400, {
            "code": "Not found",
            "message": "アップロードされた音声ファイルが不正です。"
        })

    # ファイルを保存するディレクトリのパスを取得
    dir_path_audio = file_access.json_data["dirPath"]["audioFiles"]
    dir_path_csv = file_access.json_data["dirPath"]["csvFiles"]
    # 今日の音声ファイルとcsvファイルを保存するためのディレクトリを作成
    os.makedirs(os.path.join(dir_path_audio, dir_name_today), exist_ok=True)
    os.makedirs(os.path.join(dir_path_csv, dir_name_today), exist_ok=True)

    # 午後12時以降
    if datetime.now().hour > 12:
        # 昨日以前の音声ファイルを保存していたディレクトリを削除
        dir_access = DirAccess(dir_path_audio)
        dir_access.get_dir_names()
        dir_access.remove_dir_recurse([dir_name_today])
        # 昨日以前のcsvファイルを保存していたディレクトリを削除
        dir_access = DirAccess(dir_path_csv)
        dir_access.get_dir_names()
        dir_access.remove_dir_recurse([dir_name_today])

    # 設定ファイルからfile_list.jsonのパスを取得
    file_list = FileList(file_access.json_data["filePath"]["fileList"])

    # 午前6時以降
    if datetime.now().hour > 5:
        # 昨日以前、何らかの理由で処理が中断してしまった音声ファイルが無いか検索
        list_file_name = file_list.get_name_suspend_files()

        # 検索結果ありの場合
        if len(list_file_name) > 0:
            # "state"を"error"に変更（上書き）
            for file_name in list_file_name:
                file_list.update_state_in_item(file_list.ERROR, file_name)

    # 保存されている音声ファイルの名称を一括取得
    for _, _, files in os.walk(dir_path_audio):
        if len(files) > 0:
            list_audio_file_name.extend(files)

    # 既に音声ファイルを削除しているのに、stateがdeletedになっていないものは更新
    file_list.bulk_update_state_to_deleted(list_audio_file_name)

    # 音声ファイルを保存
    audio_file.save(os.path.join(
        dir_path_audio, dir_name_today, saving_file_name
    ))
    # 音声データの情報を追加
    file_list.append_item(saving_file_name)
    # 最新の1000件以外は削除
    file_list.delete_items(1000)

    return make_response(jsonify({"result": "OK"}))


# 音声ファイルを文字起こしする
@app.route("/transcribe", methods=["GET"])
def transcribe() -> Response:
    # リクエスト受取り
    file_name_audio = request.args.get("fileNameAudio")
    # 変数宣言
    file_name_csv = f"{file_name_audio.split('.')[0]}.csv"
    file_path_audio = ""
    file_path_csv = ""
    file_list = None
    file_access = FileAccess(PATH_CONFIG_FILE)
    speech_to_text = None

    # 設定ファイルから音声ファイルとcsvファイルの保存ディレクトリを取得し、ファイルパスを作成
    file_access.read_json_file()
    file_path_audio = os.path.join(
        file_access.json_data["dirPath"]["audioFiles"],
        file_name_audio.split("_")[0],
        file_name_audio
    )
    file_path_csv = os.path.join(
        file_access.json_data["dirPath"]["csvFiles"],
        file_name_csv.split("_")[0],
        file_name_csv
    )
    file_list = FileList(file_access.json_data["filePath"]["fileList"])

    try:
        environment = file_access.json_data["environment"]["value"]
        parallel_count = file_access.json_data["parallelCount"][environment]

        while True:
            # 自分よりも前に、待機中（uploaded）又は処理中（transcribing）となっているファイルがいくつあるか確認
            uploaded_count = file_list.get_items_count_before(
                file_name_audio, file_list.UPLOADED
            )
            transcribing_count = file_list.get_items_count_before(
                file_name_audio, file_list.TRANSCRIBING
            )
            state = file_list.get_state_in_item(file_name_audio)

            # キャンセルしている場合は、このメソッドを抜ける
            if state != file_list.UPLOADED:
                return make_response(jsonify({"result": "Cancel"}))
            # ・待機中となっているファイルがある
            # ・変換処理中のファイルが●件以上ある
            # 場合は、10秒置いた後、再度確認
            elif not (
                uploaded_count == 0 and transcribing_count < parallel_count
            ):
                time.sleep(10)
            else:
                break

        # file_list.jsonのstateを更新（文字起こし中）
        file_list.update_state_in_item(file_list.TRANSCRIBING, file_name_audio)
        # 音声ファイルからテキストを作成し、csvファイルに出力
        speech_to_text = SpeechToText(file_path_audio)
        # 設定ファイルから、使用する学習モデルの名称と保存先を取得し、文字起こしを実行
        speech_to_text.transcribe(
            file_access.json_data["modelName"][environment],
            file_access.json_data["dirPath"]["model"]
        )
        speech_to_text.write_to_csv_file(file_path_csv)
        # file_list.jsonのstateを更新（文字起こし完了）
        file_list.update_state_in_item(file_list.TRANSCRIBED, file_name_audio)

        return make_response(jsonify({"result": "OK"}))
    except Exception as ex:
        print(ex)
        # file_list.jsonのstateを更新（エラー発生）
        file_list.update_state_in_item(file_list.ERROR, file_name_audio)

        abort(500, {
            "code": "Internal server error",
            "message": "予期せぬエラーが発生しました。"
        })
    finally:
        del speech_to_text
        gc.collect()


# 文字起こしのキャンセル（待機中のみ可）
@app.route("/cancelTranscribing/<file_name_audio>", methods=["DELETE"])
def cancel_transcribing(file_name_audio: str) -> Response:
    # 変数宣言
    file_path_audio = ""
    file_access = FileAccess(PATH_CONFIG_FILE)
    file_list = None

    file_access.read_json_file()
    # 設定ファイルからfile_list.jsonのパスを取得
    file_list = FileList(file_access.json_data["filePath"]["fileList"])

    try:
        # 設定ファイルから音声ファイルとcsvファイルの保存ディレクトリを取得し、ファイルパスを作成
        file_path_audio = os.path.join(
            file_access.json_data["dirPath"]["audioFiles"],
            file_name_audio.split("_")[0],
            file_name_audio
        )
        # 音声ファイルとcsvファイルを削除
        os.remove(file_path_audio)
        # file_list.jsonのstateを更新（削除完了）
        file_list.update_state_in_item(file_list.DELETED, file_name_audio)

        return make_response(jsonify({"result": "OK"}))
    except Exception as ex:
        print(ex)
        # file_list.jsonのstateを更新（エラー発生）
        file_list.update_state_in_item(file_list.ERROR, file_name_audio)

        abort(500, {
            "code": "Internal server error",
            "message": "予期せぬエラーが発生しました。"
        })


# csvファイル（文字起こしの結果）をダウンロード
@app.route("/downloadCsv", methods=["GET"])
def download_csv() -> Response:
    # リクエスト受取り
    file_name_audio = request.args.get("fileNameAudio")
    file_name_csv = request.args.get("fileNameCsv")
    # 変数宣言
    file_path_csv = ""
    file_access = FileAccess(PATH_CONFIG_FILE)
    file_list = None

    # 設定ファイルからcsvファイルの保存ディレクトリを取得し、ファイルパスを作成
    file_access.read_json_file()
    file_path_csv = os.path.join(
        file_access.json_data["dirPath"]["csvFiles"],
        file_name_csv.split("_")[0],
        file_name_csv
    )

    # 設定ファイルからfile_list.jsonのパスを取得
    file_list = FileList(file_access.json_data["filePath"]["fileList"])
    # file_list.jsonのstateを更新（ダウンロード完了）
    file_list.update_state_in_item(file_list.DOWNLOADED, file_name_audio)

    # クライアントへcsvファイルを送信
    return send_file(
        file_path_csv,
        mimetype="text/csv",
        as_attachment=True
    )


# 文字起こしの結果をjson形式でダウンロード
@app.route("/downloadJson", methods=["GET"])
def download_json() -> Response:
    # リクエスト受取り
    file_name_audio = request.args.get("fileNameAudio")
    file_name_csv = request.args.get("fileNameCsv")
    # 変数宣言
    file_path_csv = ""
    file_access = FileAccess(PATH_CONFIG_FILE)
    file_list = None
    speech_to_text = None

    # 設定ファイルからcsvファイルの保存ディレクトリを取得し、ファイルパスを作成
    file_access.read_json_file()
    file_path_csv = os.path.join(
        file_access.json_data["dirPath"]["csvFiles"],
        file_name_csv.split("_")[0],
        file_name_csv
    )
    try:
        list_result = []
        # csvファイルを読み込み、オブジェクトに戻す
        speech_to_text = SpeechToText()
        speech_to_text.convert_csv_to_obj(file_path_csv)

        # 設定ファイルからfile_list.jsonのパスを取得
        file_list = FileList(file_access.json_data["filePath"]["fileList"])
        # file_list.jsonのstateを更新（ダウンロード完了）
        file_list.update_state_in_item(file_list.DOWNLOADED, file_name_audio)
        # finally説でインスタンスを破棄する前に、必要な情報のみディープコピー
        list_result = copy.deepcopy(speech_to_text.list_segments)

        return make_response(jsonify({"segments": list_result}))
    except Exception:
        raise
    finally:
        del speech_to_text
        gc.collect()


# 音声ファイルとcsvファイルを削除
@app.route("/deleteAudioAndCsv/<file_name_audio>", methods=["DELETE"])
def delete_audio_and_csv(file_name_audio: str) -> Response:
    # 変数宣言
    file_name_csv = f"{file_name_audio.split('.')[0]}.csv"
    file_path_audio = ""
    file_path_csv = ""
    file_access = FileAccess(PATH_CONFIG_FILE)
    file_list = None

    # 設定ファイルから音声ファイルとcsvファイルの保存ディレクトリを取得し、ファイルパスを作成
    file_access.read_json_file()
    file_path_audio = os.path.join(
        file_access.json_data["dirPath"]["audioFiles"],
        file_name_audio.split("_")[0],
        file_name_audio
    )
    file_path_csv = os.path.join(
        file_access.json_data["dirPath"]["csvFiles"],
        file_name_csv.split("_")[0],
        file_name_csv
    )
    # 音声ファイルとcsvファイルを削除
    os.remove(file_path_audio)
    os.remove(file_path_csv)

    # 設定ファイルからfile_list.jsonのパスを取得
    file_list = FileList(file_access.json_data["filePath"]["fileList"])
    # file_list.jsonのstateを更新（削除完了）
    file_list.update_state_in_item(file_list.DELETED, file_name_audio)

    return make_response(jsonify({"result": "OK"}))


# ファイルの処理状況を取得
@app.route("/getStateTranscription", methods=["GET"])
def get_state_transcription() -> Response:
    # リクエスト受取り
    file_name_audio = request.args.get("fileNameAudio")
    file_access = FileAccess(PATH_CONFIG_FILE)
    file_list = None
    dict_result = {}

    # 設定ファイルからfile_list.jsonのパスを取得
    file_access.read_json_file()
    file_list = FileList(file_access.json_data["filePath"]["fileList"])
    # 処理状況をメッセージ付きで取得
    dict_result = file_list.get_state_with_msg(file_name_audio)

    return make_response(jsonify(dict_result))


# 'file_list.json'をダウンロード
@app.route("/downloadFileList", methods=["GET"])
def download_file_list() -> Response:
    # 設定ファイルからfile_list.jsonのパスを取得
    file_access = FileAccess(PATH_CONFIG_FILE)
    file_access.read_json_file()

    # クライアントへcsvファイルを送信
    return send_file(
        file_access.json_data["filePath"]["fileList"],
        mimetype="application/json",
        as_attachment=True
    )


# apiの接続テスト用
@app.route("/", methods=["GET"])
def connection_test() -> Response:
    return "接続テストOK。このURLは有効です。"


# エラーが発生したとき処理
# 400 Bad Request
# 404 Not Found
@app.errorhandler(400)
@app.errorhandler(404)
def error_handler(error):
    print(error)
    return jsonify({
        "error": {
            "code": error.description["code"],
            "message": error.description["message"]
        }
    }), error.code


# 予期せぬエラーが発生したとき
@app.errorhandler(Exception)
def error_handler_others(error):
    print(error)
    return jsonify({
        "error": {
            "code": "Internal Server Error",
            "message": "予期せぬエラーが発生しました。"
        }
    }), 500


# # Flaskアプリの起動
# if __name__ == ("__main__"):
#     # localhost以外からのアクセスを許可
#     app.run(host="0.0.0.0", port=5050, threaded=True)
