from flask import Flask

from .file_access import FileAccess


# Flaskアプリの初期設定を行うためのクラス
class AppSetting:
    # Flaskインスタンスのconfig変数を設定
    @classmethod
    def set_config(cls, app: Flask, path_config_file: str) -> None:
        environment = ""
        dict_config = {}
        file_access = FileAccess(path_config_file)

        # 外部ファイルから設定情報を取得
        file_access.read_json_file()
        environment = file_access.json_data["environment"]["value"]
        dict_config = file_access.json_data["config"][environment]

        # config変数へ代入
        app.config["ENV"] = environment
        app.config["DEBUG"] = dict_config["debug"]
        app.config["TESTING"] = dict_config["testing"]
        app.config["JSON_AS_ASCII"] = dict_config["jsonAsAscii"]
        app.config["MAX_CONTENT_LENGTH"] = dict_config["maxContentLength"]
