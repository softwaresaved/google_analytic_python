# Google Analytics (GA) website stats for a group of URLs

Given a set of URLs in a text file, a list of GA metrics to capture,
and a start and end date, provides the following reports for the given
time period:

* An overall, sorted summary of summed metrics per month
* An overall, sorted summary of pageviews per page, including a list of
URLs per page that are just variants of the same URL - i.e. they are the
same page and should be counted as such
* Individual monthly reports of pageviews per page

It uses a pre-downloaded set of monthly GA data for the entire website,
which currently exists for the period June 2015 - February 2017. Thus,
reports can only be generated within (or equal to) this current time
period unless further monthly data sets are downloaded.


## Files

### Generating reports

* [url_lists/](url_lists) - Directory of files each holding sets of pages to process,
one URL per line
* [generate_config.py](generate_config.py) - The configuration file where you specify the
start and end dates for the analysis period, the metrics you wish to
capture, and the specific file of URLs to process held in `url_lists/`
* [generate_group_stats.py](generate_group_stats.py) - The script which takes the configuration in
`generate_config.py` and produces the reports
* [reports/](reports) - Directory that holds the reports generated by
`generate_group_stats.py`
* [ga_raw_data/](ga_raw_data) - Directory that holds the pre-downloaded GA data for
entire website, used by `generate_group_stats.py`
* [logs/](logs) - Directory which holds log files for processing runs, named
`generate-<date>.log`


### Downloading GA stats data

Given the data has already been downloaded and stored in this repository,
there is no need to use this capability unless expanding the set of
overall monthly stats it can use:

* [auth_secret/](auth_secret) - Contains `client-secrets.json` file to hold credential
to authenticate with GA. See [https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py](https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py)
for details on how to obtain a usable credential based on your Google
account, using the Google Developers Console. Your Google account will
need to be first authorised within GA by a GA site administrator
* [download_config.py](download_config.py) - The configuration file to specify the start and
end dates for obtaining entire website statistics from GA, the metrics
to capture, and the Google credential to use to authenticate with GA
* [download_all_config.py](download_all_config.py) - The script which takes the configuration in
`download_config.py` and downloads the monthly website statistics from GA
* [ga_raw_data/](ga_raw_data) - Directory which will hold the downoaded monthly
statistics
* [logs/](logs) - Directory which holds log files for processing runs, named
`download-<date>.log`


## Requirements

### Generating reports

* Python 3 (tested on Python 3.6.0)
* Python libraries (installable via `pip install -r requirements.txt` - 
see `requirements.txt` for specific version details):
    * pandas
    * numpy


### Downloading GA stats data

There's no need to satisfy these requirements if you only want to
generate reports. It's only needed if you want to expand the existing
GA monthly data sets beyond the currently stored period data (see above).

In addition to the requirements for generating reports, these additional
requirements need to be satisfied:

* Python libraries
    * google-api-python-client (only needed for downloading statistics)
* Google account authorised with GA site administrator
* Generated and downloaded GA JSON credential

See [https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py](https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py)
for more details on generating a GA JSON credential.


## Generating reports

### Configuration

Edit the `generate_config.py` file and edit the following parameters:

* `STARTDATE`, `ENDDATE` - The start and end dates for the period for
which you wish to generate reports, in `YYYY-MM-DD` format
* `PAGE_METRICS` - The metrics you wish to capture. Typical ones are
for overall page views `ga:pageviews` and unique page views
`ga:uniquepageviews`. You can find others at [https://developers.google.com/analytics/devguides/reporting/core/dimsmets](https://developers.google.com/analytics/devguides/reporting/core/dimsmets),
but note that only these two have been currently tested. Note that
generated reports will be sorted by the first metric specified
* `URL_LIST_FILE` - The file of URLs you wish to generate reports
for within the time period, held in the `url_lists/` directory,
with a single URL per line


### Specifying the URLs to check, and how searching works

For each URL you wish to process, add a line to a file specified
by `URL_LIST_FILE` in `generate_config.py`. Note that these
a number of different permutations of the same URL are supported,
given the ways GA reports page hits and the different naming
conventions that have been historically supported across our
website. The ones supported, which seem to cater for at least
99.9% of cases, are:

- Those which are the exact URL, e.g. `http://software.ac.uk/blog/whats-wrong-computer-scientists`
- Those which have a date prefix, e.g. `http://software.ac.uk/blog/2013-10-31-whats-wrong-computer-scientists`
- Those which have a querystring suffix, e.g. `http://software.ac.uk/blog/2013-10-31-whats-wrong-computer-scientists?mpw=`
- Those which are a combination of the last two

Essentially, the URLs which are supplied are 'shortened' to their
core path and page 'meaning', e.g. `blog/whats-wrong-computer-scientists`,
to be used for searching. This ensures that variants of this core
page can be found. All others, which shouldn't be counted, are
ignored in statistics calculations, e.g. those with prefixes `404`,
`/search?`, etc. Any duplicates in the URL list that will
essentially match the same page more than once are ignored (so
search results are only counted once).


### Running the tool

Simply type `python generate_group_stats.py` at the command line. A
summary of progress for processing and generating reports per month,
and overall, will be displayed.


### Examining the reports

In the `reports/` directory, you should see:

* A number of Comma-Separated Value (CSV) reports with filenames matching
`ga-report-<url-file>-<year-month>.csv`, each containing summaries across
all core pages for each given metric
* A `ga-summary-<url-file>-<time-period>.csv` CSV report which contains
a monthly breakdown over the time period for the given metrics
* A `ga-complete-<url-file>-<time-period>.csv` CSV report which contains
an overall breakdown, per core page, for the given metrics

Note that each report will be sorted by the first metric specified
in `PAGE_METRICS` given in `generate_config.py`.


## Downloading GA stats data

To be completed.
