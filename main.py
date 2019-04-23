import asyncio
import time
import re
import json
from hashlib import md5
from random import randint

from aiohttp import web
from sympy.parsing.latex import parse_latex
import sympy
from passlib.hash import sha256_crypt

from problems import *
from util import NumericStringParser

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
URL_BASE = "http://localhost:5556"

class Page(web.Application):
    URL_BASE = "http://localhost:5556"

    def __init__(self):
        super().__init__()
        self.types = {
            'quadratic': quadratic,
            'systems': doubles
        }

        self.add_routes([
            web.get('/', self.get_home),
            web.get('/problem', self.get_problem),
            web.get('/login', self.get_login),
            web.get('/newaccount', self.get_signup),
            web.get('/{filename}', self.get_quill),
            web.get('/{filename}/{filename2}', self.get_quill),
        ])

        with open("templates/problem_page.html", "r") as rf:
            self.problem_page = rf.read()

        with open("templates/index.html", "r") as rf:
            self.home_page = rf.read()

        with open("templates/wipe_cookies.html", "r") as rf:
            self.WIPE_COOKIES = rf.read()

        with open("logins.json", "r") as js:
            self.auth = json.load(js)

        self.nsp = NumericStringParser()
        self.sessions = {}

    async def host(self):
        runner = web.AppRunner(self)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5556)
        await site.start()

    async def get_login(self, request: web.Request):
        if 'password' not in request.query or 'email' not in request.query:
            raise web.HTTPNetworkAuthenticationRequired()

        email = request.query['email']
        password = request.query['password']

        verified = sha256_crypt.verify(password, sha256_crypt.hash(self.auth.get(email, "")))
        print(verified)
        if not verified:
            raise web.HTTPFound(self.URL_BASE)

        sid = self.create_session(email)
        self.sessions[sid] = email
        raise web.HTTPFound(self.URL_BASE + f"/?sessionID={sid}")

    async def get_signup(self, request: web.Request):
        if 'password' not in request.query or 'email' not in request.query:
            raise web.HTTPNetworkAuthenticationRequired()

        email = request.query['email']
        if not EMAIL_REGEX.fullmatch(email):
            raise web.HTTPFound(URL_BASE)
        password = request.query['password']
        if email in self.auth:
            raise web.HTTPFound(self.URL_BASE)

        phash = sha256_crypt.hash(password)
        self.auth[email] = phash

        with open("logins.json", "w") as js:
            json.dump(self.auth, js)

        sid = self.create_session(email)
        self.sessions[sid] = email
        raise web.HTTPFound(self.URL_BASE + f"/?sessionID={sid}")

    async def get_home(self, request: web.Request):
        listing = "    \n".join("<li>{}</li>".format(x) for x in self.types)
        text = self.home_page.replace("{list}", listing)

        if 'sessionID' in request.query and request.query['sessionID'] and request.query[
            'sessionID'] not in self.sessions:
            resp = web.Response(body=self.WIPE_COOKIES)
            resp.headers['content-type'] = 'text/html'
            return resp

        resp = web.Response(body=text)
        resp.headers['content-type'] = 'text/html'
        return resp

    async def get_quill(self, request: web.Request):
        if 'filename2' in request.match_info:
            request.match_info['filename'] = request.match_info['filename'] + "/" + request.match_info['filename2']
        try:
            with open('public/' + request.match_info['filename'], 'rb') as qf:
                data = qf.read()
        except FileNotFoundError:
            raise web.HTTPNotFound()

        resp = web.Response(body=data)
        resp.headers['content-type'] = "text/" + request.match_info['filename'].strip("/").split(".")[-1]
        # print(resp.headers)
        return resp

    async def expire_session(self, sessionID):
        await asyncio.sleep(3600)
        del self.sessions[sessionID]

    async def get_problem(self, request: web.Request):
        # print(self.sessions)

        if not request.query:
            items = {
                "title": "Redirecting",
                "n": 0,
                "problems": "",
                "sessionID": ""
            }

            ftext = self.problem_page
            for k, v in items.items():
                ftext = ftext.replace(f"{{{k}}}", str(v))

            resp = web.Response(body=ftext)
            resp.headers['content-type'] = 'text/html'
            return resp

        elif "types" in request.query:
            types = request.query["types"].replace(" ", "").split(",")

            if not all(itype in self.types for itype in types):
                raise web.HTTPBadRequest(reason="Provided problem type is invalid")

            problemsData = []
            problems = ""
            temp = """<p> {n}. {quest} <span id="problem{n}"><ul><li>{eq}</li></ul></span></p> <p><span id="answer{n}"></span></p>"""
            for i, itype in enumerate(types):
                probData = self.types[itype](**request.query)
                problemsData.append(probData)
                # print("\n".join(probData[0]), probData[0])
                problems += "\n" + temp.format(n=i + 1, eq="</li><li>".join(probData[0]), quest=probData[3])

            items = {
                "title": "Insert Title Here",
                "n": len(types),
                "problems": problems,
                "sessionID": self.create_session()
            }

            self.sessions[items["sessionID"]] = problemsData
            self.loop.create_task(self.expire_session(items["sessionID"]))

            raise web.HTTPFound(self.URL_BASE + f"/problem?sessionID={items['sessionID']}")

        elif "t" in request.query and request.query['t'] == 'submit':
            if "sessionID" not in request.query:
                raise web.HTTPFound(self.URL_BASE)
            if request.query['sessionID'] not in self.sessions:
                resp = web.Response(body=self.WIPE_COOKIES)
                resp.headers['content-type'] = 'text/html'
                return resp

            session_data = self.sessions[request.query['sessionID']]
            verified = {}
            i = 0
            for prob, value in request.query.items():
                if not prob.startswith("problem"):
                    continue
                try:
                    eq, mvars, ans, quest = session_data[i]

                    value = value.replace("\\left(", "").replace("\\right)", "").replace("\\ ", "").replace(" ", "")
                    if not value:
                        verified[prob] = (*ans, False)
                    else:
                        nums = {parse_latex(x).evalf() for x in value.split(",")}  # parse_latex(value)

                        if isinstance(ans, set):
                            if len(nums) == len(ans) and all(
                                            a == b for a, b in
                                            zip(sorted({sympy.Integer(item) for item in ans}), sorted(nums))):
                                verified[prob] = *ans, True
                            else:
                                verified[prob] = *ans, False
                        elif isinstance(ans, (tuple, list)):
                            if len(nums) == len(ans) and all(
                                            a == b for a, b in
                                            zip([sympy.Integer(item) for item in ans], nums)):
                                verified[prob] = *ans, True
                            else:
                                verified[prob] = *ans, False

                except:
                    import traceback
                    traceback.print_exc()
                    verified[prob] = *ans, False

                i += 1

            ftext = "<br />".join(
                f"{k.strip('problem')}. {'correct' if p else 'incorrect'}. Answers: {', '.join(type(ans)(str(item) for item in ans))}"
                for
                k, (*ans, p) in verified.items())
            resp = web.Response(body=ftext)
            resp.headers['content-type'] = 'text/html'
            return resp

        elif "sessionID" in request.query:
            if request.query['sessionID'] not in self.sessions:
                raise web.HTTPFound(self.URL_BASE)

            problemsData = self.sessions[request.query['sessionID']]
            problems = ""
            temp = """<p> {n}. {quest} <span id="problem{n}"><ul><li>{eq}</li></ul></span></p> <p><span id="answer{n}"></span></p>"""

            print(problemsData)

            for i, prob in enumerate(problemsData):
                problems += "\n" + temp.format(n=i + 1, eq="</li><li>".join(prob[0]), quest=prob[3])

            items = {
                "title": "Insert Title Here",
                "n": len(problemsData),
                "problems": problems,
                "sessionID": self.create_session()
            }

            self.sessions[items["sessionID"]] = problemsData
            self.loop.create_task(self.expire_session(items["sessionID"]))

            ftext = self.problem_page
            for k, v in items.items():
                ftext = ftext.replace(f"{{{k}}}", str(v))

            resp = web.Response(body=ftext)
            resp.headers['content-type'] = 'text/html'
            # print(ftext)
            return resp

        else:
            raise web.HTTPBadRequest(reason="Failed to provide a problem type")

    def create_session(self, email):
        hash = md5()
        hash.update(str(time.ctime()).encode())
        hash.update(str(randint(1, 50)).encode())
        hash.update(email.encode())
        return hash.hexdigest()


l = asyncio.get_event_loop()
l.create_task(Page().host())
l.run_forever()
