import asyncio
from aiohttp import web
from random import randint

class Page(web.Application):
    def __init__(self):
        super().__init__()
        self.types = {
            'quadratic': self.quadratic
        }

        self.add_routes([
            web.get('/problem', self.get_problem),
            web.get('/{filename}', self.get_quill),
        ])

        with open("templates/problem_page.html", "r") as rf:
            self.problem_page = rf.read()

    async def host(self):
        runner = web.AppRunner(self)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5556)
        await site.start()

    async def get_quill(self, request: web.Request):
        with open('public/' + request.match_info['filename']) as qf:
            data = qf.read()

        resp = web.Response(body=data)
        resp.headers['content-type'] = request.match_info['filename'].strip("/").split(".")[-1]
        return resp

    async def get_problem(self, request: web.Request):
        if "types" not in request.query:
            raise web.HTTPBadRequest(reason="Failed to provide a problem type")

        types = request.query["types"].split(",")

        if not all(type in self.types for type in types):
            raise web.HTTPBadRequest(reason="Provided problem type is invalid")

        problems = ""
        temp = """<p> {n}. Find the solutions to  <span id="problem{n}">{eq}</span>. </p> <p><span id="answer">x=</span></p>"""
        for i, type in enumerate(types):
            problems += "\n" + temp.format(n=i + 1, eq=self.types[type](**request.query)[0])


        items = {
            "title": "Insert Title Here",
            "n": 1,
            "problems": problems
        }

        ftext = self.problem_page
        for k, v in items.items():
            ftext = ftext.replace(f"{{{k}}}", str(v))

        resp = web.Response(body=ftext)
        resp.headers['content-type'] = 'text/html'
        return resp

    def quadratic(self, **kwargs):
        if "z1" in kwargs:
            z1 = int(kwargs['z1'])
        else:
            z1 = randint(-10, 10)

        if "z2" in kwargs:
            z2 = int(kwargs['z2'])
        else:
            z2 = randint(-10, 10)

        if "k" in kwargs:
            k = kwargs['k']
        else:
            k = randint(1, 5)

        a, b, c = 1, -z1 + -z2, z1 * z2
        if a == 1:
            apart = "x^2"
        elif a != 0:
            apart = f"{a * k}x^2"
        else:
            apart = ""


        if b * k == 1:
            bpart = f"{'-' if b * k < 0 else '+'} x"
        elif b != 0:
            bpart = f"{'-' if b * k < 0 else '+'} {abs(b * k)}x"
        else:
            bpart = ""

        if c != 0:
            cpart = f"{'-' if c * k < 0 else '+'} {abs(c * k)}"
        else:
            cpart = ""

        return "{} {} {}".format(apart, bpart, cpart).strip(), [a, b, c, k, z1, z2]

l = asyncio.get_event_loop()
l.create_task(Page().host())
l.run_forever()