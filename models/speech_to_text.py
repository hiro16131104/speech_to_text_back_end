import whisper
import pandas as pd
import csv
import math
import torch


# 音声ファイルからテキストを作成するためのクラス
class SpeechToText:
    # 共通変数
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    list_model_name = [TINY, BASE, SMALL, MEDIUM, LARGE]
    # BOM付きのUTF-8（Excel対策）
    ENCODING = "utf_8_sig"

    def __init__(self, file_path_audio: str = "") -> None:
        self.file_path_audio = file_path_audio
        self.dict_result = {}
        self.list_segments = []

    # 文字起こし（cpuの場合）
    def __transcribe_cpu(
        self,
        arg_model_name: str,
        dir_path_model: str = None,
        language: str = None
    ) -> None:
        # cpuの場合、学習モデルはmediumを上限とする
        model_name = (
            self.MEDIUM if arg_model_name == self.LARGE else arg_model_name
        )
        # モデルをcpuで読み込み
        model = whisper.load_model(
            model_name, "cpu", download_root=dir_path_model
        )
        # 音声からテキストへ変換
        self.dict_result = model.transcribe(
            self.file_path_audio,
            language=language,
            beam_size=5,
            fp16=False,
            without_timestamps=True
        )

    # 文字起こし（gpuの場合）
    def __transcribe_cuda(
        self,
        model_name: str,
        dir_path_model: str = None,
        language: str = None
    ) -> None:
        # 重み情報をcpuで読み込み（gpuのメモリ節約）
        model = whisper.load_model(
            model_name, "cpu", download_root=dir_path_model
        )
        # モデルをfp32からfp16に変換し、gpuのメモリに配置する
        _ = model.half()
        _ = model.cuda()

        # LayerNormの重みだけfp32にする（これをしないと例外が発生する）
        for m in model.modules():
            if isinstance(m, whisper.model.LayerNorm):
                m.float()

        # 音声からテキストへ変換
        self.dict_result = model.transcribe(
            self.file_path_audio,
            language=language,
            beam_size=5,
            fp16=True,
            without_timestamps=True
        )

    # 文字起こし
    # learned_model（学習モデル）は、tiny,base,small,medium,largeの5種類
    def transcribe(
        self,
        model_name: str,
        dir_path_model: str = None,
        language: str = None
    ) -> None:
        # 引数のバリデーション
        if model_name not in self.list_model_name:
            raise Exception("引数'model_name'が不正です。")
        elif (
            language
            and language.lower() not in ["japanese", "english", "ja", "en"]
        ):
            raise Exception("引数languageが不正です。")

        # gpuが使える場合は、cuda用のメソッドを使用
        if torch.cuda.is_available():
            self.__transcribe_cuda(model_name, dir_path_model, language)
        else:
            self.__transcribe_cpu(model_name, dir_path_model, language)

    # 引数の「秒」を「時・分・秒」に変換し、「00:00:00」の形式で返却

    def convert_sec_to_str_time(self, arg_sec: int) -> str:
        if arg_sec < 1:
            return "00:00:00"

        sec = math.floor(arg_sec)
        min = 0
        hour = 0
        min = sec // 60
        sec = sec % 60
        hour = min // 60 if min > 0 else 0
        min = min % 60 if hour > 0 else min

        return f"{str(hour).zfill(2)}:{str(min).zfill(2)}:{str(sec).zfill(2)}"

    # 文字起こしの結果をcsvファイルに出力
    def write_to_csv_file(self, file_path_csv: str) -> None:
        # DataFrameに変換
        df_segments = pd.DataFrame(self.dict_result["segments"])
        # 不要な列を削除
        df_segments.drop(
            columns=["seek", "tokens", "temperature", "avg_logprob",
                     "compression_ratio", "no_speech_prob"],
            inplace=True
        )

        # 秒の列を「00:00:00」に変換（更新）
        for idx, item in df_segments.iterrows():
            new_value_start = self.convert_sec_to_str_time(int(item["start"]))
            new_value_end = self.convert_sec_to_str_time(int(item["end"]))
            df_segments.loc[idx, "start"] = new_value_start
            df_segments.loc[idx, "end"] = new_value_end

        # csvファイルに出力(パラメータ"utf_8_sig"は、Excel対策)
        df_segments.to_csv(
            file_path_csv, index=False, encoding=self.ENCODING,
            quoting=csv.QUOTE_NONNUMERIC
        )

    # csvファイルを読み込み、オブジェクトに戻す
    def convert_csv_to_obj(self, file_path_csv: str) -> None:
        df_segments = pd.read_csv(file_path_csv, encoding=self.ENCODING)
        # 変換後の例:[{"X":"aa", "Y":"pp"},{"X":"bb", "Y":"qq"}]
        self.list_segments = df_segments.to_dict(orient="records")
