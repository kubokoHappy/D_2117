from flask import render_template, request, redirect, flash
import flask_login
from waitress import serve
from web.form import *
from web.database import *
from werkzeug.utils import secure_filename
import os


"""完了済み"""

login_manager = flask_login.LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])  # ログイン
def login():
    if flask_login.current_user.is_authenticated:  # すでにログイン中なら/に飛ばす
        return redirect("/")

    form = LogInForm(request.form)
    if form.validate_on_submit():
        userlogin = UserLogin.query.filter_by(
            email=form.email.data).one_or_none()

        if userlogin is None or not userlogin.check_password(form.password.data):
            return "ログインに失敗"

        userlogin.login()  # ログイン時刻を記録
        try:
            db.session.add(userlogin)  # 最終ログイン時刻の記録
            db.session.commit()
        except:
            pass

        user = User.query.filter_by(email=form.email.data).one_or_none()
        flask_login.login_user(user)  # flaskloginにログイン中のユーザに登録

        return redirect("/")  # ログインに成功したらトップページへ移動

    return render_template("login.html", form=form)


@app.route("/logout", methods=['GET'])  # ログアウトページ
@ flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect("/")


@app.route("/memberInfo", methods=["GET", "POST"])  # 新規会員情報入力ページ
def memberInfo():
    form = MemberInfoForm(request.form)
    if form.validate_on_submit():
        new_user = User(form.user_nickname.data, form.user_fname.data, form.user_lname.data,
                        form.email.data, form.tell.data, form.prefecture.data, form.city.data)
        new_user_pass = UserLogin(form.email.data, form.password.data)
        try:
            db.session.add(new_user)
            db.session.add(new_user_pass)
            db.session.commit()
        except:
            return "登録失敗"

        return redirect("/login")
    return render_template("memberInfo.html", form=form)


@app.route("/petInfo", methods=["GET", "POST"])  # ペットの登録
@ flask_login.login_required
def petInfo():
    form = PetInfoForm(request.form)
    if form.validate_on_submit():
        new_pet = Pet(flask_login.current_user.id,
                      form.pet_name.data, form.features_description.data)
        try:
            db.session.add(new_pet)
            db.session.commit()
        except:
            return "登録失敗"
        return redirect("/")
    return render_template("petInfo.html", form=form)


@app.route("/searchPet", methods=["GET", "POST"])  # ペット探し
def searchPet():
    form = SearchPetForm(request.form)
    if form.validate_on_submit():
        # 画像を加工・保存
        img = request.files['img']
        if img is None:
            return "画像を登録してください"
        filename = secure_filename(img.filename)
        img_url = os.path.join('search', filename)
        img.save(os.path.join(app.config['UPLOAD_FOLDER'], img_url))
        """
        AI関連の記述する部分
        """
        del img  # メモリ対策
        new_searchpet = SearchPet(
            form.prefecture.data, form.city.data, form.features_description.data, img_url, "test")
        try:
            db.session.add(new_searchpet)
            db.session.commit()
        except:
            return "登録失敗"
        return redirect("/")

    return render_template("searchPet.html", form=form)


@ app.route("/", methods=["GET", "POST"])
@ app.route("/<reply_id>", methods=["GET", "POST"])  # トップページ(スレッド一覧)
def thread(reply_id="0"):
    if reply_id.isdigit() == False:
        reply_id = 0
    if int(reply_id) < 0:
        reply_id = 0
    reply_id = int(reply_id)

    threadlist = Thread.query.filter_by(reply_id=reply_id)

    if reply_id == 0:
        threadlist = threadlist.order_by(Thread.thread_id.desc())
    else:
        threadlist = threadlist.order_by(Thread.thread_id)

    # スレッドの作成にはログイン、ペットの登録がいる
    # 返信にはログインがいる

    form = ThreadForm(request.form)

    if flask_login.current_user.is_authenticated:

        pet_list = Pet.query.filter_by(
            user_id=flask_login.current_user.id).all()
        if len(pet_list) > 0:
            # ペットの名前をセレクトできるように
            form.pet_id.choices = [(pet.pet_id, pet.pet_name)
                                   for pet in pet_list]

        if form.validate_on_submit():
            # 画像を加工・保存
            img = request.files['img']
            filename = secure_filename(img.filename)
            if filename == '' and reply_id == 0:
                return "画像を登録してください"
            if reply_id == 0:  # トップページのスレッドは必ず写真あり
                img_url = os.path.join(form.pet_id.data, filename)
                os.makedirs(os.path.join(
                    app.config['UPLOAD_FOLDER'], form.pet_id.data), exist_ok=True)
                img.save(os.path.join(
                    app.config['UPLOAD_FOLDER'], img_url))
                """
                AI関連の記述する部分
                """
                vector = "test"
                del img
            else:
                img_url = None
                vector = None

            # DBへ保存
            new_thread = Thread(flask_login.current_user.id,
                                form.pet_id.data, reply_id, img_url, form.message.data, vector)
            try:
                db.session.add(new_thread)
                db.session.commit()
            except:
                return "登録失敗"

    return render_template("thread.html", form=form, reply_id=reply_id, threadlist=threadlist.all())


"""開発中"""


@ app.route("/myPage", methods=["GET"])  # マイページ
@ flask_login.login_required
def myPage():
    pet_list = Pet.query.filter_by(
        user_id=flask_login.current_user.id).all()
    return redirect("/petInfo.html", pet_list=pet_list)


"""未完成"""


@ app.route("/memberInfoFix", methods=["GET"])  # 会員情報修正ページ
@ flask_login.login_required
def memberInfoFix():
    return render_template("memberInfoFix.html")


"""サーバの起動"""


def main():
    app.run(host='0.0.0.0', port=7777, debug=True)
    # serve(app, host='0.0.0.0', port=5000)
