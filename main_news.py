import json
import re
from datetime import datetime, date
import requests
from flask import Flask, render_template, request, flash
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
local_server = True
with open('config.json', 'r') as c:
    params = json.load(c) ['params']
app.secret_key = params['secret_key']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USERNAME=params ['user_gmail'],
    MAIL_PASSWORD=params ['password_gmail'],
    MAIL_DEFAULT_SENDER=params ['user_gmail'],
    MAIL_USE_TLS=False,
    MAIL_USE_SSL=True,
)
mail = Mail(app)


if local_server:
    app.config ['SQLALCHEMY_DATABASE_URI'] = params ['local_uri']
else:
    app.config ['SQLALCHEMY_DATABASE_URI'] = params ['prod_uri']

db = SQLAlchemy(app)


class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    subject = db.Column(db.String(15), unique=True, nullable=False)
    message = db.Column(db.String(300), unique=False, nullable=False)


class Articles(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(5000), nullable=True)
    img = db.Column(db.String(600), nullable=True)
    url = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(6), nullable=False)


def NewsParse (api_url):
    total_results =[]
    news_dict = True
    page = 1
    while news_dict:
        news = requests.get(f'{api_url}&page={page}').json()
        news_dict = news.get('articles',[])
        total_results.extend(news_dict)
        page += 1

    img = []
    title = []
    desc = []
    url = []
    date_list = []

    for i in range(len(total_results)):
        articles = total_results [i]
        img.append(articles ['urlToImage'])
        title.append(articles ['title'])
        desc.append(articles ['description'])
        url.append(articles ['url'])
        date_list.append(articles ['publishedAt'])
    today = date.today()

    for i in range(len(date_list)):
        match = re.search('\d{4}-\d{2}-\d{2}', date_list [i])
        date_only = datetime.strptime(match.group(), '%Y-%m-%d').date()
        if today == date_only:
            month = today.strftime('%B')
            day = today.strftime('%d')
            year = today.strftime('%Y')
    return [img, title, desc, url, month, day, year]

def write_json(data, filename='config.json'):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

with open('config.json', 'r') as c:
    params = json.load(c)

    temp = params['params']
    api_url =temp ['api_key']
    lst = NewsParse(api_url)
    title_1= lst[1][0]
    title_2= lst[1][1]
    img_1 = lst[0][0]
    img_2 = lst[0][1]
    url_1 = lst[3][0]
    url_2 = lst[3][1]

    latest_news = {"latest_news_1": title_1,
                   "latest_news_2": title_2,
                   "latest_news_img1": img_1,
                   "latest_news_img2": img_2,
                   "latest_news_url1" : url_1,
                   "latest_news_url2" : url_2}
    temp.update(latest_news)
write_json(params)

with open('config.json','r') as c:
    params = json.load(c) ['params']

per_page = params['per_page']
@app.route("/")
def home ():

    Articles.query.delete()
    db.session.commit()

    api_url = params['api_key']
    lst = NewsParse(api_url)
    img = lst[0]
    title = lst[1]
    desc =lst[2]
    url = lst [3]
    month = lst [4]
    day = lst [5]
    year = lst [6]
    date = datetime.now()
    mylist = zip(img, title, desc, url)

    for i in range(len(img)):
        sno = i+1
        data = Articles(title = title[i], description= desc[i], img = img[i], url=url[i], date=date, sno=sno)
        db.session.add(data)
        db.session.commit()

    posts = Articles.query.order_by(Articles.date.desc())
    page = request.args.get('page')

    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    pages = posts.paginate(page = page, per_page=per_page)

    return render_template('index.html', context=mylist, month=month, day=day, year=year, pages=pages, params=params)


@app.route("/about")
def about ():
    return render_template('about.html', params=params)


@app.route("/contact", methods=['GET', 'POST'])
def contact ():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        entry = Contact(name=name, email=email, subject=subject, message=message)
        db.session.add(entry)
        db.session.commit()
        mail.send_message(f'New message {name}',
                          recipients=[params ['user_gmail']],
                          body=f'{subject} \n {message}')
        flash('Thanks')
    return render_template('contact.html', params=params)


@app.route("/covid_dashboard")
def covidDashboard ():
    url = params ['covid_api']
    headers = {
        'x-rapidapi-host': params['covid_api_host'],
        'x-rapidapi-key': params['covid_api_key']
    }
    response = requests.request("GET", url, headers=headers)

    count_dict = json.loads(response.text)
    total_india = count_dict ['state_data']

    state = []
    active = []
    total = []
    recover = []
    deceased = []

    for i in range(len(total_india)):
        cases = total_india [i]
        active.append(cases ['active'])
        total.append(cases ['confirmed'])
        recover.append(cases ['recovered'])
        deceased.append(cases ['deaths'])
        state.append(cases ['state'])

    list_count = zip(active, total, recover, deceased, state)

    world_url = params ['world_api']
    headers = {
        'x-rapidapi-host': params['world_api_host'],
        'x-rapidapi-key': params['world_api_key']
    }

    response = requests.request("GET", world_url, headers=headers)

    count_dict = json.loads(response.text)
    total_world = count_dict [0] ['Total Cases_text']
    active_world = count_dict [0] ['Active Cases_text']
    recover_world = count_dict [0] ['Total Recovered_text']
    deceased_world = count_dict [0] ['Total Deaths_text']

    total_india = count_dict [2] ['Total Cases_text']
    active_india = count_dict [2] ['Active Cases_text']
    recover_india = count_dict [2] ['Total Recovered_text']
    deceased_india = count_dict [2] ['Total Deaths_text']

    return render_template('covid_dashboard.html', context=list_count, total_world=total_world,
                           active_world=active_world, recover_world=recover_world,
                           deceased_world=deceased_world, total_india=total_india, active_india=active_india,
                           recover_india=recover_india,
                           deceased_india=deceased_india, params=params)


app.run(debug=True)
