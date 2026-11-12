// SPDX-FileCopyrightText: 2026 ai.pycal.org contributors
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// Show the times of the page in the local time of the browser, like GitHub: the text says how
// long ago, the title the exact local time. The server already wrote both in UTC
// (ai_pycal/templatetags/times.py, with the same rules), so the page works without this script.
"use strict";

(function () {
  const RELATIVE_DAYS = 30;
  const language = document.documentElement.lang || undefined;
  // dateStyle and timeStyle cannot be combined with timeZoneName
  const exact = new Intl.DateTimeFormat(language, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
  const day = new Intl.DateTimeFormat(language, { dateStyle: "medium" });
  const relative = new Intl.RelativeTimeFormat(language, { numeric: "auto" });

  function ago(time, now) {
    const seconds = (now - time) / 1000;
    if (seconds < 45) return relative.format(0, "second");
    const minutes = Math.round(seconds / 60);
    if (minutes < 60) return relative.format(-minutes, "minute");
    const hours = Math.round(seconds / 3600);
    if (hours < 24) return relative.format(-hours, "hour");
    const days = Math.round(seconds / 86400);
    if (days < RELATIVE_DAYS) return relative.format(-days, "day");
    return "on " + day.format(time);
  }

  function update() {
    const now = Date.now();
    // exact times, such as the version of an agreement: the local time, without "ago"
    for (const element of document.querySelectorAll("time.when-exact[datetime]")) {
      const time = new Date(element.getAttribute("datetime"));
      if (!Number.isNaN(time.getTime())) element.textContent = exact.format(time);
    }
    for (const element of document.querySelectorAll("time.when[datetime]")) {
      const time = new Date(element.getAttribute("datetime"));
      if (Number.isNaN(time.getTime())) continue;
      element.textContent = ago(time, now);
      element.title = exact.format(time);
    }
  }

  update();
  setInterval(update, 60 * 1000);
})();
