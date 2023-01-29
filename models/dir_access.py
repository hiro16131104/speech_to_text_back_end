import os
import shutil


# ディレクトリにアクセスするためのクラス
class DirAccess:
    def __init__(self, dir_path: str) -> None:
        # アクセスするディレクトリの相対パス
        self.dir_path = dir_path
        self.list_file_names = []
        self.list_dir_names = []

    # ディレクトリ直下にあるファイルの名称を取得
    def get_file_names(self) -> None:
        # ディレクトリ直下のアイテム名を取得
        list_item_names = os.listdir(self.dir_path)
        self.list_file_names = []

        # ファイルのみ抽出
        self.list_file_names = list(filter(
            lambda x: os.path.isfile(os.path.join(self.dir_path, x)),
            list_item_names
        ))

    # ディレクトリ直下にある子ディレクトリの名称を取得
    def get_dir_names(self) -> None:
        # ディレクトリ直下のアイテム名を取得
        list_item_names = os.listdir(self.dir_path)
        self.list_dir_names = []

        # ディレクトリのみ抽出
        self.list_dir_names = list(filter(
            lambda x: os.path.isdir(os.path.join(self.dir_path, x)),
            list_item_names
        ))

    # ディレクトリ直下にある子ディレクトリを削除
    # 削除対象から除外するディレクトリも設定可
    def remove_dir_recurse(self, list_ignore_dir_name: list[str] = []) -> None:
        # 削除対象
        list_target_dir_name = []

        if len(list_ignore_dir_name) > 0:
            # 除外ディレクトリ以外を抽出
            list_target_dir_name = list(filter(
                lambda x: x not in list_ignore_dir_name,
                self.list_dir_names
            ))
        else:
            list_target_dir_name = self.list_dir_names

        # サブディレクトリも含めて削除
        for dir_name in list_target_dir_name:
            shutil.rmtree(os.path.join(self.dir_path, dir_name))
