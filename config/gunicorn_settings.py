# アプリケーション・サーバー（gunicorn）の設定ファイル

wsgi_app = "main:app"
bind = "0.0.0.0:5000"
proc_name = 'infrastructure_flask'
workers = 2
reload = True
