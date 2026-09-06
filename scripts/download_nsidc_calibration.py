#!/usr/bin/env python

from __future__ import print_function

import base64
import itertools
import json
import math
import netrc
import os
import ssl
import sys
import time
from getpass import getpass

try:
    from urllib.parse import urlparse
    from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
    from urllib.error import HTTPError, URLError
except ImportError:
    from urlparse import urlparse
    from urllib2 import (
        urlopen,
        Request,
        HTTPError,
        URLError,
        build_opener,
        HTTPCookieProcessor,
    )


# ============================================================================
# CONFIGURATION
# ============================================================================

SHORT_NAME = "NSIDC-0051"
VERSION = "2"

CMR_URL = "https://cmr.earthdata.nasa.gov"
URS_URL = "https://urs.earthdata.nasa.gov"

CMR_PAGE_SIZE = 2000

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "raw",
    "nsidc",
)

# Southern Hemisphere bounding box.
# We only need the region containing the selected iceberg trajectories.
BOUNDING_BOX = "-180,-90,180,-39.23"

# --------------------------------------------------------------------------
# Selected calibration windows
#
# Each window has one extra day before and after the original 7-day window.
# --------------------------------------------------------------------------

DATE_RANGES = [
    ("2019-02-22T00:00:00Z", "2019-03-03T23:59:59Z"),
    ("2020-08-23T00:00:00Z", "2020-09-01T23:59:59Z"),
    ("2021-05-23T00:00:00Z", "2021-06-01T23:59:59Z"),
    ("2022-10-31T00:00:00Z", "2022-11-09T23:59:59Z"),
    ("2022-12-17T00:00:00Z", "2022-12-26T23:59:59Z"),
    ("2023-06-13T00:00:00Z", "2023-06-24T23:59:59Z"),
    ("2023-07-28T00:00:00Z", "2023-08-12T23:59:59Z"),
]

FILE_DOWNLOAD_MAX_RETRIES = 3


# ============================================================================
# AUTHENTICATION
# ============================================================================

def get_username():
    try:
        do_input = raw_input
    except NameError:
        do_input = input

    return do_input(
        "Earthdata username (or press Return to use a bearer token): "
    )


def get_password():
    password = ""

    while not password:
        password = getpass("Earthdata password: ")

    return password


def get_token():
    token = ""

    while not token:
        token = getpass("Earthdata bearer token: ")

    return token


def get_login_credentials():
    """Get Earthdata credentials from .netrc or prompt."""

    credentials = None
    token = None

    try:
        info = netrc.netrc()

        username, _account, password = info.authenticators(
            urlparse(URS_URL).hostname
        )

        if username == "token":
            token = password
        else:
            credentials_string = "{0}:{1}".format(
                username,
                password,
            )

            credentials = base64.b64encode(
                credentials_string.encode("ascii")
            ).decode("ascii")

    except Exception:
        username = None
        password = None

    if not username:
        username = get_username()

        if len(username):
            password = get_password()

            credentials_string = "{0}:{1}".format(
                username,
                password,
            )

            credentials = base64.b64encode(
                credentials_string.encode("ascii")
            ).decode("ascii")

        else:
            token = get_token()

    return credentials, token


# ============================================================================
# CMR QUERY
# ============================================================================

def build_version_query_params(version):
    desired_pad_length = 3

    if len(version) > desired_pad_length:
        raise ValueError(
            'Version string too long: "{0}"'.format(version)
        )

    version = str(int(version))

    query_params = ""

    while len(version) <= desired_pad_length:
        padded_version = version.zfill(desired_pad_length)

        query_params += "&version={0}".format(
            padded_version
        )

        desired_pad_length -= 1

    return query_params


def build_query_params_str(
    short_name,
    version,
    time_start="",
    time_end="",
    bounding_box=None,
    polygon=None,
    filename_filter=None,
    provider=None,
):

    params = "&short_name={0}".format(short_name)

    params += build_version_query_params(version)

    if time_start or time_end:
        params += "&temporal[]={0},{1}".format(
            time_start,
            time_end,
        )

    if polygon:
        params += "&polygon={0}".format(polygon)

    elif bounding_box:
        params += "&bounding_box={0}".format(bounding_box)

    if filename_filter:
        params += (
            "&options[producer_granule_id][pattern]=true"
        )

        params += (
            "&producer_granule_id[]={0}{1}{0}".format(
                "*",
                filename_filter,
            )
        )

    if provider:
        params += "&provider={0}".format(provider)

    return params


def build_cmr_query_url(
    short_name,
    version,
    time_start,
    time_end,
    bounding_box=None,
    polygon=None,
    filename_filter=None,
    provider=None,
):

    params = build_query_params_str(
        short_name=short_name,
        version=version,
        time_start=time_start,
        time_end=time_end,
        bounding_box=bounding_box,
        polygon=polygon,
        filename_filter=filename_filter,
        provider=provider,
    )

    return (
        "{0}/search/granules.json?"
        "&sort_key[]=start_date"
        "&sort_key[]=producer_granule_id"
        "&page_size={1}".format(
            CMR_URL,
            CMR_PAGE_SIZE,
        )
        + params
    )


# ============================================================================
# PROVIDER
# ============================================================================

def check_provider_for_collection(
    short_name,
    version,
    provider,
):

    query_params = build_query_params_str(
        short_name=short_name,
        version=version,
        provider=provider,
    )

    url = (
        "{0}/search/collections.json?".format(CMR_URL)
        + query_params
    )

    request = Request(url)

    try:
        response = urlopen(request)

    except Exception as exc:
        print("Error checking provider:", exc)
        sys.exit(1)

    data = response.read()
    data = json.loads(data.decode("utf-8"))

    if (
        "feed" in data
        and "entry" in data["feed"]
        and len(data["feed"]["entry"]) > 0
    ):
        return True

    return False


def get_provider_for_collection(
    short_name,
    version,
):

    providers = [
        "NSIDC_CPRD",
        "NSIDC_ECS",
    ]

    for provider in providers:

        if check_provider_for_collection(
            short_name,
            version,
            provider,
        ):
            return provider

    raise RuntimeError(
        "No provider found for {0} version {1}".format(
            short_name,
            version,
        )
    )


# ============================================================================
# CMR FILTER
# ============================================================================

def cmr_filter_urls(search_results):

    if (
        "feed" not in search_results
        or "entry" not in search_results["feed"]
    ):
        return []

    entries = [
        entry["links"]
        for entry in search_results["feed"]["entry"]
        if "links" in entry
    ]

    links = list(
        itertools.chain(*entries)
    )

    urls = []
    unique_filenames = set()

    for link in links:

        if "href" not in link:
            continue

        if (
            "inherited" in link
            and link["inherited"] is True
        ):
            continue

        if (
            "rel" in link
            and "data#" not in link["rel"]
        ):
            continue

        if (
            "title" in link
            and "opendap" in link["title"].lower()
        ):
            continue

        filename = link["href"].split("/")[-1]

        # --------------------------------------------------------------
        # IMPORTANT:
        # Only download the actual NetCDF data files.
        # --------------------------------------------------------------

        if not filename.endswith(".nc"):
            continue

        if "NSIDC0051" not in filename:
            continue

        if filename in unique_filenames:
            continue

        unique_filenames.add(filename)

        urls.append(link["href"])

    return urls


# ============================================================================
# CMR SEARCH
# ============================================================================

def cmr_search(
    short_name,
    version,
    time_start,
    time_end,
    bounding_box="",
    polygon="",
    quiet=False,
):

    provider = get_provider_for_collection(
        short_name,
        version,
    )

    cmr_query_url = build_cmr_query_url(
        short_name=short_name,
        version=version,
        time_start=time_start,
        time_end=time_end,
        bounding_box=bounding_box,
        polygon=polygon,
        provider=provider,
    )

    if not quiet:
        print()
        print("Searching:")
        print(cmr_query_url)
        print()

    cmr_paging_header = "cmr-search-after"

    cmr_page_id = None

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    urls = []
    hits = 0

    while True:

        request = Request(cmr_query_url)

        if cmr_page_id:
            request.add_header(
                cmr_paging_header,
                cmr_page_id,
            )

        try:
            response = urlopen(
                request,
                context=ctx,
            )

        except Exception as exc:
            print("Error:", exc)
            sys.exit(1)

        headers = {
            key.lower(): value
            for key, value in dict(
                response.info()
            ).items()
        }

        if not cmr_page_id:

            hits = int(
                headers.get(
                    "cmr-hits",
                    0,
                )
            )

            if not quiet:
                print(
                    "Found {0} matching granules.".format(
                        hits
                    )
                )

        cmr_page_id = headers.get(
            cmr_paging_header
        )

        search_page = response.read()

        search_page = json.loads(
            search_page.decode("utf-8")
        )

        page_urls = cmr_filter_urls(
            search_page
        )

        if not page_urls:
            break

        urls.extend(page_urls)

        if not cmr_page_id:
            break

    return urls


# ============================================================================
# DOWNLOAD HELPERS
# ============================================================================

def cmr_read_in_chunks(
    file_object,
    chunk_size=1024 * 1024,
):

    while True:

        data = file_object.read(
            chunk_size
        )

        if not data:
            break

        yield data


def get_speed(
    time_elapsed,
    chunk_size,
):

    if time_elapsed <= 0:
        return ""

    speed = chunk_size / time_elapsed

    if speed <= 0:
        speed = 1

    size_name = (
        "",
        "k",
        "M",
        "G",
        "T",
        "P",
        "E",
        "Z",
        "Y",
    )

    i = int(
        math.floor(
            math.log(speed, 1000)
        )
    )

    p = math.pow(1000, i)

    return "{0:.1f}{1}B/s".format(
        speed / p,
        size_name[i],
    )


def output_progress(
    count,
    total,
    status="",
    bar_len=60,
):

    if total <= 0:
        return

    fraction = min(
        max(
            count / float(total),
            0,
        ),
        1,
    )

    filled_len = int(
        round(
            bar_len * fraction
        )
    )

    percents = int(
        round(
            100.0 * fraction
        )
    )

    bar = (
        "=" * filled_len
        + " " * (bar_len - filled_len)
    )

    fmt = "  [{0}] {1:3d}%  {2}   ".format(
        bar,
        percents,
        status,
    )

    print(
        "\b" * (len(fmt) + 4),
        end="",
    )

    sys.stdout.write(fmt)
    sys.stdout.flush()


# ============================================================================
# AUTHENTICATED RESPONSE
# ============================================================================

def get_login_response(
    url,
    credentials,
    token,
):

    opener = build_opener(
        HTTPCookieProcessor()
    )

    request = Request(url)

    if token:

        request.add_header(
            "Authorization",
            "Bearer {0}".format(token),
        )

    elif credentials:

        try:
            response = opener.open(request)

            url = response.url

        except HTTPError:
            pass

        except Exception as exc:
            print(
                "Error{0}: {1}".format(
                    type(exc),
                    str(exc),
                )
            )
            sys.exit(1)

        request = Request(url)

        request.add_header(
            "Authorization",
            "Basic {0}".format(
                credentials
            ),
        )

    try:

        response = opener.open(request)

    except HTTPError as exc:

        error = "HTTP error {0}, {1}".format(
            exc.code,
            exc.reason,
        )

        if "Unauthorized" in str(exc.reason):

            if token:
                error += ": Check your bearer token."

            else:
                error += ": Check your username and password."

            print(error)
            sys.exit(1)

        raise

    except Exception as exc:

        print(
            "Error{0}: {1}".format(
                type(exc),
                str(exc),
            )
        )

        sys.exit(1)

    return response


# ============================================================================
# DOWNLOAD
# ============================================================================

def cmr_download(
    urls,
    credentials,
    token,
):

    if not urls:
        return 0, 0, 0

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    downloaded = 0
    skipped = 0
    failed = 0

    print()
    print(
        "Downloading {0} NSIDC files...".format(
            len(urls)
        )
    )
    print(
        "Output directory:",
        OUTPUT_DIR,
    )
    print()

    for index, url in enumerate(
        urls,
        start=1,
    ):

        filename = url.split("/")[-1]

        output_path = os.path.join(
            OUTPUT_DIR,
            filename,
        )

        print(
            "[{0}/{1}] {2}".format(
                index,
                len(urls),
                filename,
            )
        )

        # --------------------------------------------------------------
        # Skip already downloaded files
        # --------------------------------------------------------------

        if os.path.exists(output_path):

            try:

                if os.path.getsize(
                    output_path
                ) > 0:

                    print(
                        "  Already exists - skipping"
                    )

                    skipped += 1
                    continue

            except OSError:
                pass

        success = False

        for attempt in range(
            1,
            FILE_DOWNLOAD_MAX_RETRIES + 1,
        ):

            try:

                if attempt > 1:

                    print(
                        "  Retry {0}/{1}".format(
                            attempt,
                            FILE_DOWNLOAD_MAX_RETRIES,
                        )
                    )

                response = get_login_response(
                    url,
                    credentials,
                    token,
                )

                content_length = response.headers.get(
                    "content-length"
                )

                if content_length is None:
                    length = 0
                else:
                    length = int(content_length)

                chunk_size = min(
                    max(length, 1),
                    1024 * 1024,
                )

                if length > 0:
                    max_chunks = int(
                        math.ceil(
                            length / chunk_size
                        )
                    )
                else:
                    max_chunks = 0

                count = 0

                time_initial = time.time()

                with open(
                    output_path,
                    "wb",
                ) as out_file:

                    for data in cmr_read_in_chunks(
                        response,
                        chunk_size,
                    ):

                        out_file.write(data)

                        count += 1

                        if max_chunks > 0:

                            elapsed = (
                                time.time()
                                - time_initial
                            )

                            speed = get_speed(
                                elapsed,
                                count * chunk_size,
                            )

                            output_progress(
                                count,
                                max_chunks,
                                status=speed,
                            )

                if max_chunks > 0:
                    print()

                print("  Download complete")

                downloaded += 1
                success = True

                break

            except HTTPError as exc:

                print(
                    "  HTTP error {0}: {1}".format(
                        exc.code,
                        exc.reason,
                    )
                )

            except URLError as exc:

                print(
                    "  URL error:",
                    exc.reason,
                )

            except IOError as exc:

                print(
                    "  I/O error:",
                    exc,
                )

        if not success:

            print(
                "  FAILED:",
                filename,
            )

            failed += 1

    return downloaded, skipped, failed


# ============================================================================
# MAIN
# ============================================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True,
    )

    print("=" * 70)
    print("NSIDC-0051 VERSION 2 DOWNLOAD")
    print("=" * 70)

    print()
    print("Output:")
    print(OUTPUT_DIR)

    print()
    print("Date ranges:")

    for start, end in DATE_RANGES:
        print(
            "  {0} -> {1}".format(
                start[:10],
                end[:10],
            )
        )

    print()

    # --------------------------------------------------------------
    # Earthdata credentials
    # --------------------------------------------------------------

    credentials, token = get_login_credentials()

    # --------------------------------------------------------------
    # Search each date range
    # --------------------------------------------------------------

    all_urls = []
    unique_urls = set()

    for range_number, (
        time_start,
        time_end,
    ) in enumerate(
        DATE_RANGES,
        start=1,
    ):

        print()
        print("-" * 70)
        print(
            "DATE RANGE {0}/{1}".format(
                range_number,
                len(DATE_RANGES),
            )
        )

        print(
            "{0} -> {1}".format(
                time_start[:10],
                time_end[:10],
            )
        )

        urls = cmr_search(
            SHORT_NAME,
            VERSION,
            time_start,
            time_end,
            bounding_box=BOUNDING_BOX,
        )

        new_count = 0

        for url in urls:

            if url not in unique_urls:

                unique_urls.add(url)
                all_urls.append(url)
                new_count += 1

        print(
            "Files found in this range:",
            len(urls),
        )

        print(
            "New unique files:",
            new_count,
        )

    # --------------------------------------------------------------
    # Final search result
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("SEARCH COMPLETE")
    print("=" * 70)

    print(
        "Unique .nc files found:",
        len(all_urls),
    )

    if not all_urls:

        print()
        print(
            "No NSIDC .nc files were found for the requested ranges."
        )

        return

    # --------------------------------------------------------------
    # Download
    # --------------------------------------------------------------

    downloaded, skipped, failed = cmr_download(
        all_urls,
        credentials,
        token,
    )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)

    print(
        "Files found:       ",
        len(all_urls),
    )

    print(
        "Downloaded:        ",
        downloaded,
    )

    print(
        "Already existed:   ",
        skipped,
    )

    print(
        "Failed:            ",
        failed,
    )

    print()
    print(
        "NSIDC directory:",
        OUTPUT_DIR,
    )

    print("=" * 70)


if __name__ == "__main__":
    main()