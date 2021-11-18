import os
import json
import logging

from flask import Blueprint, render_template, redirect, url_for, g, request
from tshistory_refinery.webapi import make_app as refinery_app
from tshistory_refinery import helper

from open_saturn.helper import generate_okta_secret

bp = Blueprint(
    'open_saturn',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@bp.route('/')
def index():
    return render_template(
        'summary.html',
        has_write_permission=True
    )


def init_app(config):
    tsa = helper.apimaker(config)
    app = refinery_app(config, tsa)
    return app


def make_open_app(config):
    app = init_app(config)
    app.register_blueprint(bp)
    return app


def _generate_client_secrets(path):
    secrets = generate_okta_secret()
    with open(path, 'w') as f:
        json.dump(secrets, f)


def make_okta_app(config):
    path = 'client_secrets.json'
    app = init_app(config)
    org = os.environ['OKTA_CLIENT_ORGURL']
    token = os.environ['OKTA_CLIENT_TOKEN']
    _generate_client_secrets(path)
    app.config["OIDC_CLIENT_SECRETS"] = path
    app.config["OIDC_ID_TOKEN_COOKIE_NAME"] = "oidc_token"
    app.config["OIDC_CALLBACK_ROUTE"] = "/oidc/callback"
    app.config["OIDC_SCOPES"] = ["openid", "email", "profile"]
    app.secret_key = os.environ['RANDOM_SECRET_KEY']
    from flask_oidc import OpenIDConnect
    oidc = OpenIDConnect(app)
    from okta import UsersClient as OktaClient
    okta_client = OktaClient(org, token)
    app.register_blueprint(bp)

    @app.route("/login")
    @oidc.require_login
    def login():
        """
        Force the user to login, then redirect them to the dashboard.
        """
        return "Logged"

    @app.route("/logout")
    def logout():
        """
        Force the user to login, then redirect them to the dashboard.
        """
        return oidc.logout()

    @app.route("/")
    def index():
        return render_template(
            'summary.html',
            has_write_permission=True
        )

    open_views = [
        'tshistory_rest',
        'xlapi',
        '_oidc_callback',
        'login'
    ]
    secure_views = [
        k for k in app.view_functions.keys()
        if not any(e in k for e in open_views)
    ]

    @app.before_request
    def before_request():
        g.user = None
        if oidc.user_loggedin:
            g.user = okta_client.get_user(oidc.user_getfield("sub"))
        else:
            if request.endpoint not in open_views:
                return redirect(url_for('login'))

    return app
