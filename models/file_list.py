from datetime import datetime

from .file_access import FileAccess


# 'file_list.json'を操作するためのクラス
class FileList:
    # 共通変数
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    DOWNLOADED = "downloaded"
    DELETED = "deleted"
    ERROR = "error"
    list_state = [
        UPLOADED, TRANSCRIBING, TRANSCRIBED, DOWNLOADED, DELETED, ERROR
    ]

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.file_access = None

    # jsonファイルを読み込み
    def __read_items_from_file(self) -> None:
        self.file_access = FileAccess(self.file_path)
        self.file_access.read_json_file()

    # jsonファイルに書き込み
    def __write_items_to_file(self) -> None:
        self.file_access.write_json_file()

    # キー"id"の要素で、リストを並べ替え（降順にする場合は、isDesc=True）
    def __sort_id(self, list_obj: list, isDesc: bool = False) -> list:
        return sorted(list_obj, key=lambda x: x["id"], reverse=isDesc)

    # リストから、指定したキーに指定した値が入っている要素を抽出
    def __extract_items(self, list_obj: list, key: str, value: any) -> list:
        return list(filter(lambda x: x[key] == value, list_obj))

    # 読み込んだオブジェクトに要素を追加
    def append_item(self, file_name_audio: str) -> None:
        list_file_info = []
        value_id = 0

        # jsonファイルを読み込み
        self.__read_items_from_file()
        # idの昇順で並べ替え
        list_file_info = self.__sort_id(self.file_access.json_data["data"])

        # まだdataがない場合は、1からidを付番
        if len(list_file_info) == 0:
            value_id = 1
        # 最後のidに1追加
        else:
            last_num = len(list_file_info)-1
            value_id = list_file_info[last_num]["id"]+1

        # 音声ファイルの情報を追加
        list_file_info.append({
            "id": value_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "fileName": file_name_audio,
            "state": self.UPLOADED
        })
        self.file_access.json_data["data"] = list_file_info
        # jsonファイルへ書き込み
        self.__write_items_to_file()

    # dataの要素数が指定した数を上回っていた場合、超過分のデータを古い順に削除
    def delete_items(self, limit_items_count: int) -> None:
        list_file_info = []

        # jsonファイルを読み込み
        self.__read_items_from_file()
        # idの降順で並べ替え
        list_file_info = self.__sort_id(
            self.file_access.json_data["data"], isDesc=True
        )
        # 超過していない場合は、処理を抜ける
        if len(list_file_info) < limit_items_count+1:
            return

        # 超過した古いデータを削除
        list_file_info = list_file_info[0:limit_items_count]
        # idの昇順で並べ替え
        list_file_info = self.__sort_id(list_file_info)
        self.file_access.json_data["data"] = list_file_info
        # jsonファイルへ書き込み
        self.__write_items_to_file()

    # 指定したファイル名のstateプロパティを取得
    def get_state_in_item(self, file_name: str) -> str:
        list_item = []

        # jsonファイルを読み込み
        self.__read_items_from_file()
        list_item = self.__extract_items(
            self.file_access.json_data["data"], "fileName", file_name
        )
        if len(list_item) > 0:
            return list_item[0]["state"]
        # 検索結果なしの場合は、空文字を返却
        else:
            return ""

    # 指定したファイル名の処理状況をメッセージ付きで取得
    def get_state_with_msg(self, file_name: str) -> dict:
        state = self.get_state_in_item(file_name)
        msg = ""

        # 文字起こしの処理状況を取得
        match state:
            # アップロード完了（待機中）
            case self.UPLOADED:
                uploaded_count = self.get_items_count_before(
                    file_name, self.UPLOADED
                )
                transcribing_count = self.get_items_count_before(
                    file_name, self.TRANSCRIBING
                )
                if uploaded_count == 0 and transcribing_count == 0:
                    msg = "まもなく変換処理を開始します。"
                else:
                    # 待機中の件数には自分も含めるため、プラス1する
                    msg = f"処理が混雑しているため、待機しています。（待機中: {uploaded_count + 1}件）"
            # 変換処理中
            case self.TRANSCRIBING:
                msg = "音声からテキストへの変換処理中です。"
            # 変換処理完了
            case self.TRANSCRIBED:
                msg = "変換処理が完了しました。"
            # ダウンロード完了
            case self.DOWNLOADED:
                msg = "ダウンロードが完了しました。"
            # 削除完了
            case self.DELETED:
                msg = "削除済みのため、サーバーにファイルはありません。"
            # エラー発生
            case self.ERROR:
                msg = "エラーが発生したため、処理を中断します。"
            # 検索結果なし
            case "":
                uploaded_count = self.get_items_count(self.UPLOADED)
                transcribing_count = self.get_items_count(self.TRANSCRIBING)
                msg = "音声ファイルをアップロードしてください。"

                if uploaded_count == 0 and transcribing_count == 0:
                    msg += "（すぐに利用できます）"
                else:
                    msg += f"（待機中: {uploaded_count}件）"
            # 予期せぬエラー
            case _:
                raise Exception("'file_list.json'の検索時に予期せぬエラーが発生しました。")

        return {"state": state, "msg": msg}

    # 指定したファイル名のstateプロパティを更新
    def update_state_in_item(self, new_state: str, file_name: str) -> None:
        list_file_info = []
        dict_target = {}

        # バリデーション
        if new_state not in self.list_state:
            raise Exception("引数'new_state'が不正です。")

        # jsonファイルを読み込み
        self.__read_items_from_file()
        list_file_info = self.file_access.json_data["data"]
        # 音声ファイルの情報を更新
        dict_target = self.__extract_items(
            list_file_info, "fileName", file_name
        )[0]
        dict_target["state"] = new_state
        list_file_info = list(
            filter(lambda x: x["id"] != dict_target["id"], list_file_info))
        list_file_info.append(dict_target)
        # idの昇順で並べ替え
        self.file_access.json_data["data"] = self.__sort_id(list_file_info)
        # jsonファイルへ書き込み
        self.__write_items_to_file()

    # 一括でstateをdeletedに更新（更新対象から除外するファイルの名称を引数に渡す）
    def bulk_update_state_to_deleted(
        self, list_ignore_file_name: list[str]
    ) -> None:
        list_file_info = []

        # jsonファイルを読み込み
        self.__read_items_from_file()
        # 既に音声ファイルを削除しているのに、stateがdeletedになっていないものを抽出
        list_file_info = list(filter(
            lambda x:
            x["fileName"] not in list_ignore_file_name
            and x["state"] != self.DELETED,
            list(self.file_access.json_data["data"])
        ))
        # stateをdeletedに更新
        for item in list_file_info:
            self.update_state_in_item(self.DELETED, item["fileName"])

    # 指定した状態（state）のファイルがいくつあるか取得
    def get_items_count(self, state: str) -> int:
        list_file_info = []

        # jsonファイルを読み込み
        self.__read_items_from_file()
        # stateを条件に要素を抽出
        list_file_info = self.__extract_items(
            self.file_access.json_data["data"], "state", state
        )
        return len(list_file_info)

    # 指定したファイルよりも前に、指定した状態（state）のファイルがいくつあるか取得
    def get_items_count_before(self, fileName: str, state: str) -> int:
        list_file_info = []

        # jsonファイルを読み込み
        self.__read_items_from_file()
        list_file_info = self.file_access.json_data["data"]
        # 基準となる要素を抽出
        anchor_item = self.__extract_items(
            list_file_info, "fileName", fileName
        )[0]
        # 基準となる要素より前の要素を取得
        list_file_info = list(filter(
            lambda x: x["id"] < anchor_item["id"], list_file_info
        ))
        # stateを条件に要素を抽出
        list_file_info = self.__extract_items(
            list_file_info, "state", state
        )
        return len(list_file_info)

    # 昨日以前、何らかの理由で処理が中断してしまった音声ファイルの"fileName"を取得
    def get_name_suspend_files(self) -> list[int]:
        list_file_info = []

        # jsonファイルを読み込み
        self.__read_items_from_file()
        # 昨日以前のアイテムを抽出
        list_file_info = list(filter(
            lambda x: x["date"] != datetime.now().strftime("%Y-%m-%d"),
            self.file_access.json_data["data"]
        ))
        # 検索結果がない場合、処理を抜ける
        if len(list_file_info) == 0:
            return []

        # "state"が"uploaded"又は"transcribing"であるアイテムを抽出
        list_file_info = list(filter(
            lambda x: x["state"] in [self.UPLOADED, self.TRANSCRIBING],
            list_file_info
        ))
        # アイテムの"fileName"を抽出し、新たなリストを作成
        return list(map(lambda x: x["fileName"], list_file_info))
