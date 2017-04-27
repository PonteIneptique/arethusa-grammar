from flask import Flask, render_template, request, send_file
import json
import time
import csv
import zipfile
from io import StringIO, BytesIO

app = Flask(__name__, template_folder="./templates", static_folder="./static")


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/example1')
def example1():
    return render_template("example1.html")


@app.route('/output', methods=["POST"])
def output():
    missings = []
    fields = {
        "separator": "CSV Separator",
        "config": "Configuration name",
        "lang": "Language Morphology Tagging Set"
    }
    for field in fields.keys():
        if field not in request.form or len(request.form[field]) == 0:
            missings.append(fields[field])

    if "csvfile" not in request.files:
        missings.append("CSV File")
    else:
        f = request.files["csvfile"].read().decode()
        if len(f) == 0:
            missings.append("CSV File")
        elif len(missings) == 0:
            rows = []
            try:
                data = csv.reader(StringIO(f), delimiter=request.form.get("separator"))

                if request.form.get("header"):
                    start = 1
                else:
                    start = 0

                rows = [row for row in list(data)[start:]]
            except Exception:
                return render_template("index.html", error="Error while reading the CSV. Check your input")

            driver = {
              "plugins": {
                "morph": {
                  "noRetrieval": "online",
                  "retrievers": {
                    "BspMorphRetriever": {
                      "resource": "morphologyServiceLat"
                    }
                  },
                  "@include": "./arethusa.morph/{}.json".format(request.form.get("lang"))
                },
                "relation": {
                  "@include": "./arethusa.relation/rel.{}.json".format(request.form.get("config"))
                }
              }
            }
            config = {
                "relations": {
                    "labels": {

                    }
                }
            }
            try:
                last_row = None
                for row in rows:
                    if last_row is not None and len(row[0]) == 0:
                        tmp = config["relations"]["labels"][last_row[2]]
                        if "nested" not in tmp:
                            tmp["nested"] = {}
                        obj = tmp["nested"]
                    else:
                        last_row = row
                        obj = config["relations"]["labels"]

                    obj[row[2]] = {
                        "short": row[2],
                        "long": last_row[0] + row[1]
                    }
            except IndexError:
                return render_template("index.html", error="There seems to be an issue with the CSV file you uploaded. Check the formatting")

    if len(missings) > 0:
        return render_template("index.html", error=", ".join(missings) + " field(s) are missing or wrong")
    else:
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            files = [
                ("configs/{}.json".format(request.form.get("config")), json.dumps(driver)),
                ("configs/arethusa.relation/rel.{}.json".format(request.form.get("config")), json.dumps(config)),
            ]
            for path, content in files:
                data = zipfile.ZipInfo(path)
                data.date_time = time.localtime(time.time())[:6]
                data.compress_type = zipfile.ZIP_DEFLATED
                data.external_attr = 0o777 << 16
                zf.writestr(data, content)
        memory_file.seek(0)
        return send_file(memory_file, attachment_filename='arethusa-{}.zip'.format(request.form.get("config")), as_attachment=True)

    #return Response(
    #    zp.content,
    #    mimetype='application/zip',
    #    headers={'Content-Disposition':'attachment;filename=zones.zip'}
    #)


if __name__ == '__main__':
    app.debug = True
    app.run()
