// Date Utility Functions for College Football Ranking System
// Provides consistent date formatting across all views

/**
 * Format game date for display with optional relative dates
 * @param {string|null} dateString - ISO date string from API
 * @param {boolean} useRelative - Use relative dates for nearby games (default: false)
 * @returns {string} Formatted date or "TBD"
 *
 * @example
 * formatGameDate("2025-12-21T19:00:00Z", false)  // "Sat, Dec 21"
 * formatGameDate("2025-12-21T19:00:00Z", true)   // "Tomorrow" (if applicable)
 * formatGameDate(null)                            // "TBD"
 */
function formatGameDate(dateString, useRelative = false) {
  if (!dateString) {
    return 'TBD';
  }

  try {
    const date = new Date(dateString);

    // Use relative date if requested and applicable
    if (useRelative) {
      const relative = getRelativeDate(date);
      if (relative) return relative;
    }

    // Default format: "Day, Mon DD" (e.g., "Sat, Dec 21")
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
  } catch (e) {
    console.warn('Invalid date format:', dateString, e);
    return 'TBD';
  }
}

/**
 * Get relative date description for upcoming games
 * @param {Date} date - Game date
 * @returns {string|null} Relative description or null if > 6 days away
 *
 * Returns:
 * - "Today" for games today
 * - "Tomorrow" for games tomorrow
 * - "In X days" for games 2-6 days away
 * - null for games 7+ days away (use absolute date)
 *
 * @example
 * getRelativeDate(new Date('2025-12-23'))  // "Today" (if today is Dec 23)
 * getRelativeDate(new Date('2025-12-24'))  // "Tomorrow"
 * getRelativeDate(new Date('2025-12-26'))  // "In 3 days"
 * getRelativeDate(new Date('2026-01-01'))  // null (use absolute date)
 */
function getRelativeDate(date) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const gameDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  const diffTime = gameDate - today;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Tomorrow';
  if (diffDays > 1 && diffDays <= 6) return `In ${diffDays} days`;

  // Return null for games 7+ days away - caller should use absolute date
  return null;
}

/**
 * Get full date/time string for tooltips
 * @param {string|null} dateString - ISO date string from API
 * @returns {string} Full formatted date/time or empty string
 *
 * @example
 * getFullDateTime("2025-12-21T19:00:00Z")
 * // "Saturday, December 21, 2025, 7:00 PM EST"
 */
function getFullDateTime(dateString) {
  if (!dateString) return '';

  try {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short'
    });
  } catch (e) {
    console.warn('Invalid date format for tooltip:', dateString, e);
    return '';
  }
}

/**
 * Check if a game date is in the past
 * @param {string|null} dateString - ISO date string from API
 * @returns {boolean} True if game date is in the past
 */
function isGameInPast(dateString) {
  if (!dateString) return false;

  try {
    const gameDate = new Date(dateString);
    const now = new Date();
    return gameDate < now;
  } catch (e) {
    return false;
  }
}

/**
 * Format date for mobile view (shorter format)
 * @param {string|null} dateString - ISO date string from API
 * @returns {string} Abbreviated date or "TBD"
 *
 * @example
 * formatGameDateMobile("2025-12-21T19:00:00Z")  // "12/21"
 */
function formatGameDateMobile(dateString) {
  if (!dateString) return 'TBD';

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'numeric',
      day: 'numeric'
    });
  } catch (e) {
    return 'TBD';
  }
}
