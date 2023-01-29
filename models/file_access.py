import json


# ファイルにアクセスするためのクラス
class FileAccess:
    def __init__(self, file_path: str, encoding: str = "utf-8") -> None:
        # アクセスするファイルの相対パス
        self.file_path = file_path
        # 文字コード
        self.encoding = encoding
        self.json_data = {}

    # jsonファイルを読み込む
    def read_json_file(self) -> None:
        # カレントディレクトリは、呼び出し元である点に注意
        with open(self.file_path, "r", encoding=self.encoding) as file:
            self.json_data = json.loads(file.read())

    # jsonファイルに書き込む（洗い替え）
    def write_json_file(self) -> None:
        # カレントディレクトリは、呼び出し元である点に注意
        with open(self.file_path, "w", encoding=self.encoding) as file:
            json.dump(self.json_data, file, indent=4, ensure_ascii=False)
