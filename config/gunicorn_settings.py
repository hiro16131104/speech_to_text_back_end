# アプリケーション・サーバー（gunicorn）の設定ファイル

# mainファイルのappインスタンス
wsgi_app = "main:app"
# ipアドレス+port番号
# bind = "0.0.0.0:5000"
# 任意の名称
proc_name = "infrastructure_flask"
# ワーカースレッド数
workers = 2
# デバッグ時、ソースコードを自動反映
reload = True
