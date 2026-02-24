from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import TypingTest, Result
import json
import statistics
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from django.db.models import Prefetch

def home(request):
    tests = TypingTest.objects.filter(active=True)
    return render(request, "base.html", {"tests": tests})

@login_required
def dashboard(request):
    tests = TypingTest.objects.filter(active=True)
    return render(request, "competition/dashboard.html", {"tests": tests})


@login_required
def take_test(request, test_id):
    test = get_object_or_404(TypingTest, id=test_id, active=True)

    if test.start_time and timezone.now() < test.start_time:
        return render(request, "competition/waiting.html", {"test": test})

    return render(request, "competition/test.html", {"test": test})


@login_required
def submit_result(request):
    if request.method == "POST":
        data = request.POST

        disqualified = data.get("disqualified") == "true"

        wpm = int(float(data["wpm"]))
        accuracy = float(data["accuracy"])
        time_taken = float(data["time"])
        tab_switches = int(data["tab_switches"])
        paste_attempts = int(data["paste_attempts"])
        backspace_count = int(data.get("backspace_count", 0))
        test_id = int(data["test_id"])

        suspicious = False
        if wpm > 180 or tab_switches > 0 or paste_attempts > 0:
            suspicious = True

        keystrokes_raw = data.get("keystrokes", "[]")


        keystrokes = json.loads(keystrokes_raw)

        avg_interval = 0
        suspicious = False

        if len(keystrokes) > 5:
            intervals = [keystrokes[i+1] - keystrokes[i]
                        for i in range(len(keystrokes)-1)]
            avg_interval = sum(intervals) / len(intervals)

            # If too consistent or too fast → suspicious
            if avg_interval < 50:  # <50ms per key = likely bot
                suspicious = True
            if statistics.pstdev(intervals) < 5:  # too uniform = script
                suspicious = True

        Result.objects.create(
            user=request.user,
            test_id=test_id,
            wpm=wpm,
            accuracy=accuracy,
            time_taken=time_taken,
            tab_switches=tab_switches,
            paste_attempts=paste_attempts,
            backspace_count=backspace_count,
            keystroke_data=keystrokes,
            avg_key_interval=avg_interval,
            suspicious=suspicious,
            disqualified=disqualified
        )

        return JsonResponse({"status": "ok"})

    if request.method == "POST":
        data = request.POST

        wpm = int(data["wpm"])
        accuracy = float(data["accuracy"])
        time_taken = float(data["time"])
        tab_switches = int(data["tab_switches"])
        paste_attempts = int(data["paste_attempts"])
        test_id = int(data["test_id"])

        suspicious = False
        if wpm > 180 or tab_switches > 0 or paste_attempts > 0:
            suspicious = True

        Result.objects.update_or_create(
    user=request.user,
    test_id=test_id,
    defaults={
        "wpm": wpm,
        "accuracy": accuracy,
        "time_taken": time_taken,
        "tab_switches": tab_switches,
        "paste_attempts": paste_attempts,
        "backspace_count": backspace_count,
        "keystroke_data": keystrokes,
        "avg_key_interval": avg_interval,
        "suspicious": suspicious,
        "disqualified": disqualified,
    }
)


        return JsonResponse({"status": "ok"})


def leaderboard(request):
    tests = TypingTest.objects.filter(active=True).order_by("id").prefetch_related(
        Prefetch(
            "result_set",
            queryset=Result.objects.filter(suspicious=False, disqualified=False)
                                   .select_related("user")
                                   .order_by("-wpm", "-accuracy"),
            to_attr="ordered_results"
        )
    )

    return render(request, "competition/leaderboard.html", {
        "tests": tests
    })


def rank_list(request, test_id):
    results = Result.objects.filter(test_id=test_id, disqualified=False, suspicious=False)\
                            .order_by("-wpm", "-accuracy")
    return render(request, "competition/rank_list.html", {"results": results})



def generate_certificate(request, result_id):
    result = Result.objects.get(id=result_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="certificate.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("Certificate of Participation", styles["Title"]))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"This is to certify that <b>{result.user.profile.full_name}</b>", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Scored {result.wpm} WPM with {result.accuracy}% accuracy.", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("In the Typing Competition.", styles["Normal"]))

    doc.build(story)
    return response


def rules(request):
    return render(request, "competition/rules.html")
