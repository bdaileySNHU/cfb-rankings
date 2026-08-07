// Paging helper for list endpoints.
//
// The API caps `limit` at 500 while a full season runs ~900 games, so a single
// request silently truncates to whichever rows sort first. Callers that need
// the whole list must page.

(function (global) {
  'use strict';

  /**
   * Collect every page from a paged endpoint.
   *
   * @param {function(number, number): Promise<Array>} fetchPage - called with
   *   (skip, limit); returns one page.
   * @param {number} [pageSize=500] - rows per request.
   * @returns {Promise<Array>} every row, in page order.
   */
  async function fetchAllPages(fetchPage, pageSize) {
    var size = pageSize || 500;
    var all = [];
    for (var skip = 0; ; skip += size) {
      var page = await fetchPage(skip, size);
      all = all.concat(page);
      // A short page means we reached the end. An exactly-full final page costs
      // one extra empty request, which is cheaper than trusting a total count
      // the endpoint does not return.
      if (page.length < size) return all;
    }
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { fetchAllPages: fetchAllPages };
  }
  global.fetchAllPages = fetchAllPages;
})(typeof globalThis !== 'undefined' ? globalThis : this);
