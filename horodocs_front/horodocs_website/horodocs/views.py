import requests
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from horodocs.forms import HorodatageForm

from horodocs_website.settings import API_KEY, API_URL
from django.utils.translation import get_language


@login_required(login_url="login/")
def horodocs(request):
    """Logic used by the Server when the user goes to /add. Requires login.

    3 cases are possible :

        1. The user is new to the page, so we generate a normal page with a form.
        2. The user submit the form with completed value so we redirect all parameters to the API. A JSONResponse will tell the success/failure of this operation.
        3. The user submit the form but an error occured.

    :param request: Request by the user
    :type request: Django Request
    :return: Dependent of the user request
    :rtype: HttpResponse or JSONResponse
    """

    if request.method == "POST":
        form = HorodatageForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            data["language"] = get_language()
            full_url = API_URL + "add_leaf_tree/"
            headers = {"x-api-key": API_KEY}
            response = requests.post(full_url, headers=headers, json=data, verify=False)
            if response.ok:
                return JsonResponse({"status": "valid request"}, status=200)
            elif response.status_code == 503:
                return JsonResponse({"status": "horodating not available"}, status=503)
            else:
                return JsonResponse(
                    {"status": "an error occured"}, status=response.status_code
                )
        else:
            print("invalid form")
            return JsonResponse({"status": "bad form"}, status=400)
    else:
        form = HorodatageForm()
        context = {
            "form": form,
            "redirect_to": '/add'
        }
    return render(request, "horodocs/horodocs.html", context)


def index(request):
    """Homepage of the website

    :param request: User request
    :type request: Django Request
    :return: Loaded homepage
    :rtype: HttpResponse
    """
    context = {"redirect_to": '/'}
    return render(request, "horodocs/index.html", context)


def verification(request):
    """Verification page. The website redirects parameters to the API and display the API response. The page can be empty if some informations are missing or if the verification is not yet available.
    Needed parameters (informations) are :
    salt, date, md5, sha256, the anterior branches, the posterior branches and the version

    :param request: User request
    :type request: Django Request
    :return: Verification's success or failure
    :rtype: HttpResponse
    """
    dict_get = request.GET.copy()
    if all(
        k in dict_get
        for k in (
            "salt",
            "date",
            "md5",
            "sha256",
            "anterior_branches",
            "posterior_branches",
            "version",
        )
    ):
        full_url = API_URL + "verify_receipt/"
        dict_get["language"] = get_language()
        headers = {"x-api-key": API_KEY}
        response = requests.get(full_url, params=dict_get, headers=headers, verify=False)
        if response.ok:
            context = response.json()
            context['redirect_to'] = '/verification?'+request.GET.urlencode()
            return render(request, "horodocs/verification.html", context)
    return render(request, "horodocs/verification.html", {"validation": 5})


def hash(request):
    """Hashpage of the website. Use to only hash a file. Looks a lot like the /add route.

    :param request: User request
    :type request: Django Request
    :return: Loaded Hashpage
    :rtype: HttpResponse
    """
    context = {'redirect_to': '/hash'}
    return render(request, "horodocs/hash.html", context)
