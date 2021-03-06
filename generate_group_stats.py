"""Given a set of website URLs, search time period, and monthly raw website
   Google Analytics data:
    * Search raw monthly GA data for URLs
    * For each month, generate summary total report for metrics, save to file
    * Generate and save an overall summary report, aggregating all monthly data
"""

import os
import sys
import re
import pandas as pd
import logging
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from datetime import datetime

from generate_config import (LOGFILE_DIR,
    STARTDATE, ENDDATE, PAGE_METRICS, GA_OUTPUT_DIR, URL_LIST_FILE,
    REP_OUTPUT_DIR)


SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
DISCOVERY_URI = ('https://analyticsreporting.googleapis.com/$discovery/rest')
VIEW_ID = '31084866'  # The SSI software.ac.uk view id

# Regexps for matching optional page prefixes and query suffixes on pages
URL_REGEXP_DATEOPTION = '(?:[0-9]{4}-[0-9]{2}-[0-9]{2}-){0,1}'
URL_REGEXP_QUERYOPTION = '(?:\?.*){0,1}$'
URL_REGEXP_PATHPREFIX = '^[^\?&]*/'

# Set default logging (only set if none already defined)
logfile = 'generate-' + datetime.now().strftime('%Y-%m-%d') + '.log'
logging.basicConfig(filename=os.path.join(LOGFILE_DIR, logfile),
                    format='%(asctime)s - %(levelname)s %(funcName)s() - %(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)


def extract_core_url(url):
  """Extract core page from URL, removing any date prefix and querystring.

  :param url: str URL to process
  :return: str pair of core page name
  """
  # Extract the path and page from the URL
  url_path = urlparse(url).path
  path, page = os.path.split(url_path.strip())

  # Remove any fixed date already prefixed to page name, to increase chances
  # we'll find any duplicate content (with perhaps other fixed date prefixes)
  core_page = re.sub('^' + URL_REGEXP_DATEOPTION, '', page)

  return core_page


def build_regexp_url(core_page):
    """Build regexp to search for pages with optional date prefix and querystring.

    :param core_page: str the core page to search for
    :return: the built regular expression
    """
    # Our regular expression to find our page, with an optional date prefix in page
    # name and optional HTTP get query, so we can group stats for all aliases/copies
    # of same actual content. Note we ignore the URL path prefix entirely
    url_regexp = URL_REGEXP_PATHPREFIX + URL_REGEXP_DATEOPTION + core_page + URL_REGEXP_QUERYOPTION
    return url_regexp


def calculate_search_terms(url_file):
    """Generate a list of unique core pages to search for based on file of URLs.

    :param url_file: str the file of URLs, one per line
    :return: list of unique core pages, including paths
    """
    core_pages = {}
    file = open(url_file, 'r')
    for url in file:
        if url[0] == '#':
            continue

        core_page = extract_core_url(url)

        # Only register it as a core page if it isn't an empty string
        if core_page:
            core_pages[core_page] = build_regexp_url(core_page)

    file.close()

    return core_pages


def summarise_by_core_pages(search_terms, df):
  """Search for pages matching core URLs, return summary data for found pages.

  :param search_terms: list of core page and regular expression to search for
  :param df: dataframe to search
  :return: dataframe containing summary of all found pages
  """
  new_df = pd.DataFrame(columns=df.columns.values)
  for core_page, page_regexp in search_terms.items():
    log.debug("Calculating for " + core_page + ", using regexp:")
    log.debug(page_regexp)

    # Find all pages matching our core page regular expression
    idx = df['ga:pagepath'].str.contains(page_regexp)
    log.debug("Found " + df[idx]['ga:pagepath'].to_string())

    # Create summary totals of metrics for found pages, adding
    # to our summary DataFrame
    sum_metrics = df[idx][PAGE_METRICS].apply(pd.to_numeric).sum(axis=0, numeric_only=True)
    sum_metrics.at['Pages'] = df[idx]['ga:pagepath'].str.cat(sep=',')
    sum_metrics.at['ga:pagepath'] = core_page
    new_df = new_df.append(sum_metrics, ignore_index=True)
    log.debug("Metrics: \n" + str(sum_metrics))

    # We don't want to count found ones twice, remove them
    # from search dataframe
    df = df[~idx]

  return new_df


def main():
    # Lambda convenience function to split string by comma into list, remove
    # blank entries, remove duplicates by converting to a set
    remove_page_duplicates = lambda x: ', '.join(set(filter(None, x.split(','))))

    # The entire search date range and column data we want
    startdate = datetime.strptime(STARTDATE, '%Y-%m-%d')
    enddate = datetime.strptime(ENDDATE, '%Y-%m-%d')

    # The suffix we add to our csv filenames
    csv_report_suffix = '-' + startdate.strftime('%Y-%m') + '--' + enddate.strftime('%Y-%m')

    # Create directory path for where we'll put the reports, extracting the
    # filename from URL_LIST_FILE and disregarding any subdirectory or extension
    # Any reports that already exist will be overridden by any later versions
    _, out_full_filename = os.path.split(URL_LIST_FILE)
    out_filename, _ = os.path.splitext(out_full_filename)
    output_dir = os.path.join(REP_OUTPUT_DIR, out_filename + csv_report_suffix)

    # If our output directory doesn't exist, create it
    if not os.path.exists(output_dir):
        log.info("Creating new report directory " + output_dir + "...")
        os.makedirs(output_dir)
    else:
        log.info("Reports will be generated in existing report directory " + output_dir + "...")

    # To contain overall summaries, per-month and per-year
    mo_summary_df = pd.DataFrame(columns=['Year', 'Month']+PAGE_METRICS)
    yr_summary_df = pd.DataFrame(columns=['Year']+PAGE_METRICS)

    # To contain an overall summary, per core page
    complete_df = pd.DataFrame(columns=['ga:pagepath']+['Pages']+PAGE_METRICS)

    # Get our set of search terms from URL_LIST_FILE
    search_terms = calculate_search_terms(URL_LIST_FILE)

    # Iterate through date range on a monthly basis,
    # processing GA data for that month based on url list
    report_startdate = startdate
    while report_startdate <= enddate:
        report_enddate = report_startdate + relativedelta(months=1) - relativedelta(days=1)
        csv_in_filename = 'ga-report-' + report_startdate.strftime('%Y-%m') + '.csv'
        csv_out_filename = ('ga-report-' + os.path.basename(URL_LIST_FILE) + '-'
                           + report_startdate.strftime('%Y-%m') + '.csv')

        if not os.path.exists(os.path.join(GA_OUTPUT_DIR, csv_in_filename)):
            log.error("Could not find GA raw data csv file " + csv_in_filename)
            print("**** Could not find GA raw data csv file " + csv_in_filename)
            sys.exit(1)

        log.info("Processing " + csv_in_filename + "...")
        print("Processing " + csv_in_filename + "...")
        monthly_df = pd.read_csv(os.path.join(GA_OUTPUT_DIR, csv_in_filename),
                                 index_col=0)

        # Create a monthly reports subdirectory if it doesn't exist
        monthly_output_dir = os.path.join(output_dir, "monthly_reports")
        if not os.path.exists(monthly_output_dir):
            log.info("Creating new monthly report subdirectory " + monthly_output_dir + "...")
            os.makedirs(monthly_output_dir)
        else:
            log.info("Monthly reports will be generated in existing monthly report subdirectory "
                     + monthly_output_dir + "...")

        log.info("Extracting monthly summary data for specified URLs")
        monthly_df = summarise_by_core_pages(search_terms, monthly_df)
        monthly_df = monthly_df.sort_values(by=PAGE_METRICS[0], ascending=False)
        monthly_df[PAGE_METRICS] = monthly_df[PAGE_METRICS].astype(int)
        monthly_df.to_csv(os.path.join(monthly_output_dir, csv_out_filename), encoding='utf-8')

        log.info("Integrating monthly stat totals into summary dataframe")
        summary = monthly_df.sum(numeric_only=True)
        summary.at['Year'] = report_startdate.strftime('%Y')
        summary.at['Month'] = report_startdate.strftime('%m')
        mo_summary_df = mo_summary_df.append(summary, ignore_index=True)

        log.info("Integrating page groupings and stats into summary dataframe")
        complete_df = complete_df.append(monthly_df, ignore_index=True)

        # Calculate our next monthly time period
        report_startdate = report_startdate + relativedelta(months=1)

    # Generate a yearly summary
    yr_summary_df = mo_summary_df.groupby(['Year'], as_index=False).sum()
    yr_summary_df = yr_summary_df.drop(columns=['Month'])

    # For our complete pages report, create aggregate views of:
    #  - all common core pages, summing all numeric columns (e.g. metrics)
    #  - all string columns (e.g. the page lists)
    # Then merge them on ga:pagepath
    c1 = complete_df.groupby('ga:pagepath', as_index=False).sum()
    c2 = complete_df.groupby('ga:pagepath').agg(lambda x: ','.join(set(x))).reset_index()
    complete_df = pd.merge(c1, c2, on=['ga:pagepath', 'Pages'], how='outer')

    # Remove any duplicate full page entries in each Pages row
    complete_df['Pages'] = complete_df['Pages'].map(remove_page_duplicates)
    # Finally, sort by first metric in PAGE_METRICS
    complete_df = complete_df.sort_values(by=PAGE_METRICS[0], ascending=False)

    # Save our summary report dataframes as CSV
    log.info("Saving summary reports...")
    print("Saving summary reports...")
    reports = [['ga-summary-monthly-', mo_summary_df], ['ga-summary-yearly-', yr_summary_df], ['ga-complete-', complete_df]]
    for filename_prefix, df in reports:
        csv_filename = (filename_prefix + os.path.basename(URL_LIST_FILE)
                        + csv_report_suffix + ".csv")
        df[PAGE_METRICS] = df[PAGE_METRICS].fillna(0).astype(int)
        log.info("Saving aggregate GA report " + csv_filename)
        df.to_csv(os.path.join(output_dir, csv_filename),
                  encoding='utf-8', index=False)


if __name__ == '__main__':
    main()
