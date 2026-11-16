from flask import Flask, request, render_template_string, Response

from pipeline import run_pipeline
from report import to_markdown

app = Flask(__name__)
LAST = {"report": None}

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>RepoRepair</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
pre { background: #f5f5f5; padding: 1rem; overflow: auto; }
.ok { color: green; } .bad { color: #b00; }
</style></head><body>
<h1>Fault Localization and Self-Validated Repair</h1>
<form method="post">
  <input name="url" size="70" placeholder="https://github.com/user/repo" required>
  <button type="submit">Analyze and repair</button>
</form>
{% if error %}<p class="bad">{{ error }}</p>{% endif %}
{% if report %}
  <p>Files analyzed: {{ report.files_analyzed }}. Code chunks indexed: {{ report.chunks_indexed }}.</p>
  <p><a href="/download">Download full report (.md)</a></p>
  <h2>Errors detected: {{ report.errors_found|length }}</h2>
  <ul>
  {% for e in report.errors_found %}
    <li><b>{{ e.file }}:{{ e.line }}</b> [{{ e.kind }}] {{ e.message }}</li>
  {% endfor %}
  </ul>
  {% for r in report.repairs %}
    <h3>{{ r.target.file }}:{{ r.target.line }} &mdash;
      <span class="{{ 'ok' if r.status == 'validated' else 'bad' }}">{{ r.status }}</span>
      ({{ r.attempts }} step(s))</h3>
    {% if r.cause %}<p><b>Cause:</b> {{ r.cause }}</p>{% endif %}
    {% if r.explanation %}<p>{{ r.explanation }}</p>{% endif %}
    {% if r.diff %}<pre>{{ r.diff }}</pre>{% endif %}
    {% if r.steps %}
    <details><summary>Agent steps ({{ r.steps|length }})</summary>
      <ul>{% for s in r.steps %}<li>{{ s.action }}: {{ s.detail }}</li>{% endfor %}</ul>
    </details>{% endif %}
    {% if r.context %}
    <details><summary>Retrieved code context ({{ r.context|length }} chunks)</summary>
      {% for h in r.context %}
        <p><b>{{ h.file }}</b> ({{ h.name }}, lines {{ h.start }}-{{ h.end }}, score {{ h.score }})</p>
        <pre>{{ h.code }}</pre>
      {% endfor %}
    </details>{% endif %}
  {% endfor %}
  <h2>Errors remaining after repair: {{ report.remaining_errors|length }}</h2>
{% endif %}
</body></html>"""


@app.route("/", methods=["GET", "POST"])
def home():
    report, error = None, None
    if request.method == "POST":
        try:
            report = run_pipeline(request.form.get("url", ""))
            LAST["report"] = report
        except Exception as exc:
            error = f"Could not complete analysis: {exc}"
    return render_template_string(PAGE, report=report, error=error)


@app.route("/download")
def download():
    if not LAST["report"]:
        return "No report yet. Run an analysis first.", 404
    return Response(to_markdown(LAST["report"]), mimetype="text/markdown",
                    headers={"Content-Disposition": "attachment; filename=repair_report.md"})


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=5002)