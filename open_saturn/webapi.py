import os
import json

from flask import (
    Blueprint,
    render_template,
    url_for,
    redirect,
    g
)

from tshistory_refinery.webapi import make_app as refinery_app
from tshistory_refinery import helper

from open_saturn.helper import generate_okta_secret


def make_open_app(config):
    tsa = helper.apimaker(config)
    app = refinery_app(config, tsa)

    bp = Blueprint(
        'open_saturn',
        __name__,
        template_folder='templates',
        static_folder='static',
    )

    @bp.route('/')
    def welcome():

        return render_template(
            'summary.html',
            has_write_permission=True
        )

    app.register_blueprint(bp)
    return app


def _generate_client_secrets(path):
    secrets = generate_okta_secret()
    with open(path, 'w') as f:
        json.dump(secrets, f)


def make_okta_app(config):
    path = 'client_secrets.json'
    app = make_open_app(config)
    org = os.environ['OKTA_CLIENT_ORGURL']
    token = os.environ['OKTA_CLIENT_TOKEN']
    _generate_client_secrets(path)
    app.config["OIDC_CLIENT_SECRETS"] = path
    app.config["OIDC_CALLBACK_ROUTE"] = "/oidc/callback"
    app.config["OIDC_SCOPES"] = ["openid", "email", "profile"]
    app.config["OIDC_ID_TOKEN_COOKIE_NAME"] = "oidc_token"
    app.secret_key = os.environ['RANDOM_SECRET_KEY']
    from flask_oidc import OpenIDConnect
    oidc = OpenIDConnect(app)
    from okta.client import Client as OktaClient
    config = {'orgUrl': org, 'token': token}
    okta_client = OktaClient(config)

    def _before_request():
        if oidc.user_loggedin:
            g.user = okta_client.get_user(oidc.user_getfield("sub"))
        else:
            g.user = None

    @app.before_first_request
    @oidc.require_login
    def login():
        _before_request()
        return redirect(url_for("/"))


    app.before_request(_before_request)

    
    return app
