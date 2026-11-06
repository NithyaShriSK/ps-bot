const form = document.querySelector("#query-form");
const question = document.querySelector("#question");
const submit = document.querySelector("#submit-btn");
const answerSection = document.querySelector("#answer-section");
const chat = document.querySelector("#chat");
const charCount = document.querySelector("#char-count");
const clearButton = document.querySelector("#clear-btn");
const content = document.querySelector(".content");
const sessionKey = "skillquery-session-id";

let sessionId = localStorage.getItem(sessionKey);
if (!sessionId) {
  sessionId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  localStorage.setItem(sessionKey, sessionId);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatColumnHeader(column) {
  const map = {
    roll_number: "Roll Number",
    name: "Student Name",
    dept_code: "Dept Code",
    department: "Department",
    completed_levels: "Completed Levels",
    total_levels_cleared: "Completed Levels",
    cleared_courses: "Courses / Levels Cleared",
    attempted_courses: "Attempted Courses",
    attempts_recorded: "Attempts",
    attempts: "Attempts",
    student_count: "Student Count",
    course_name: "Course Name",
    vertical_name: "Category",
    venue_name: "Venue",
    date: "Date",
    start_time: "Start Time",
    end_time: "End Time",
    status: "Status"
  };
  if (map[column]) return map[column];
  return column.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function getColumnClass(prefix, column) {
  const map = {
    roll_number: "roll",
    name: "name",
    dept_code: "dept-code",
    department: "dept",
    completed_levels: "levels",
    total_levels_cleared: "levels",
    cleared_courses: "courses",
    attempted_courses: "courses",
    status: "status",
    student_count: "count"
  };
  const key = map[column] || "generic";
  return `${prefix}-${key}`;
}

function organizeColumns(columns, isStudentTable) {
  if (!isStudentTable) return [...columns];
  const canonicalOrder = [
    "roll_number",
    "name",
    "dept_code",
    "department",
    "completed_levels",
    "total_levels_cleared",
    "attempts",
    "attempts_recorded",
    "cleared_courses",
    "attempted_courses"
  ];
  const sorted = [];
  canonicalOrder.forEach(col => {
    if (columns.includes(col)) sorted.push(col);
  });
  columns.forEach(col => {
    if (!sorted.includes(col)) sorted.push(col);
  });
  return sorted;
}

function createCourseBadge(courseStr) {
  const pill = document.createElement("span");
  pill.className = "course-pill";
  pill.title = courseStr;

  const match = courseStr.match(/^(.*?)\s*[-–·]\s*(Level\s*[\w\d]+|Lvl\s*[\w\d]+)$/i);
  if (match) {
    const nameSpan = document.createElement("span");
    nameSpan.className = "course-pill-name";
    nameSpan.textContent = match[1].trim();

    const lvlSpan = document.createElement("span");
    lvlSpan.className = "course-pill-lvl";
    lvlSpan.textContent = match[2].trim();

    pill.append(nameSpan, lvlSpan);
  } else {
    const textSpan = document.createElement("span");
    textSpan.className = "course-pill-name";
    textSpan.textContent = courseStr;
    pill.appendChild(textSpan);
  }
  return pill;
}

function addMessage(role, text, options = [], tableData = null) {
  const message = document.createElement("div");
  message.className = `chat-message ${role}`;
  if (role === "user") {
    message.textContent = text;
  } else {
    const avatar = document.createElement("div");
    avatar.className = "answer-avatar";
    avatar.textContent = "S";
    const body = document.createElement("div");
    body.className = "message-body";
    const label = document.createElement("p");
    label.className = "answer-label";
    label.textContent = "SkillQuery assistant";
    const contentEl = document.createElement("div");
    contentEl.className = "answer";

    // Always render textual summary and explanations
    renderAnswer(contentEl, text, options.length > 0);
    body.append(label, contentEl);

    // If metadata contains included courses description, render explanation note
    if (tableData && tableData.meta && tableData.meta.description) {
      const note = document.createElement("div");
      note.className = "taxonomy-note";
      note.innerHTML = `<strong>Domain Scope:</strong> ${escapeHtml(tableData.meta.description)}`;
      body.appendChild(note);
    }

    const hasStudentTable = tableData && Array.isArray(tableData.rows) && tableData.rows.length > 0
      && Array.isArray(tableData.columns) && tableData.columns.length > 0
      && tableData.columns.some(c => ["name", "roll_number", "student_count", "course_name", "department", "dept_code"].includes(c));

    if (hasStudentTable) {
      message.classList.add("has-table");
      body.appendChild(createTable(tableData.columns, tableData.rows, tableData.meta));
    }

    if (options.length) {
      const optionList = document.createElement("div");
      optionList.className = "option-list";
      const optionSubmit = document.createElement("button");
      optionSubmit.className = "option-submit";
      optionSubmit.type = "button";
      optionSubmit.textContent = "Submit selection";
      optionSubmit.disabled = true;
      let selectedNumber = null;
      options.forEach(({number, label: optionLabel}) => {
        const option = document.createElement("button");
        option.className = "option-button";
        option.type = "button";
        option.innerHTML = `<span>${number}</span>${escapeHtml(optionLabel)}`;
        option.addEventListener("click", () => {
          selectedNumber = number;
          optionSubmit.disabled = false;
          optionList.querySelectorAll(".option-button").forEach((item) => item.classList.remove("selected"));
          option.classList.add("selected");
        });
        optionList.appendChild(option);
      });
      optionSubmit.addEventListener("click", () => {
        question.value = String(selectedNumber);
        question.dispatchEvent(new Event("input"));
        form.requestSubmit();
      });
      optionList.appendChild(optionSubmit);
      body.appendChild(optionList);
    }
    message.append(avatar, body);
  }
  chat.appendChild(message);
  message.scrollIntoView({behavior: "smooth", block: "nearest"});
}

function createTable(columns, rows, meta = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = "table-wrap";

  const totalRows = rows.length;
  const totalMatching = meta.total_matching_students || totalRows;
  const isRank = meta.output_format === "RANK";
  const pageSize = 50;
  const totalPages = Math.ceil(totalRows / pageSize) || 1;
  let currentPage = 1;

  // Determine table properties
  const isStudentTable = columns.some(c => ["roll_number", "name"].includes(c));
  const hasCoursesCol = columns.some(c => ["cleared_courses", "attempted_courses"].includes(c));
  const addRank = isRank || (totalRows > 1 && isStudentTable);

  // Canonical column organization
  const organizedColumns = organizeColumns(columns, isStudentTable);

  // 1. PINNED META BAR
  const topBar = document.createElement("div");
  topBar.className = "table-meta-bar";

  const metaLeft = document.createElement("div");
  metaLeft.className = "table-meta-left";
  const metaLabel = document.createElement("span");
  metaLabel.className = "table-count-label";
  metaLeft.appendChild(metaLabel);

  const scrollHint = document.createElement("span");
  scrollHint.className = "scroll-hint";
  scrollHint.style.display = "none";
  scrollHint.textContent = "↔ Scroll table horizontally";
  metaLeft.appendChild(scrollHint);

  const metaRight = document.createElement("div");
  metaRight.className = "table-meta-right";

  let toggleAllBtn = null;
  let allExpanded = false;
  if (hasCoursesCol) {
    toggleAllBtn = document.createElement("button");
    toggleAllBtn.type = "button";
    toggleAllBtn.className = "table-toggle-all-btn";
    toggleAllBtn.innerHTML = `<span>Expand All</span> ▾`;
    metaRight.appendChild(toggleAllBtn);
  }

  topBar.append(metaLeft, metaRight);

  // 2. DEDICATED HORIZONTAL SCROLLING WRAPPER
  const scrollWrap = document.createElement("div");
  scrollWrap.className = "table-scroll-container";

  const table = document.createElement("table");
  table.className = "student-table";
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");

  // Rank Header
  if (addRank) {
    const rankHeader = document.createElement("th");
    rankHeader.className = "th-rank";
    rankHeader.textContent = "#";
    headerRow.appendChild(rankHeader);
  }

  // Column Headers
  organizedColumns.forEach((column) => {
    const cell = document.createElement("th");
    cell.className = getColumnClass("th", column);
    cell.textContent = formatColumnHeader(column);
    headerRow.appendChild(cell);
  });
  head.appendChild(headerRow);

  const body = document.createElement("tbody");

  // Pagination controls elements
  const prevBtn = document.createElement("button");
  prevBtn.type = "button";
  prevBtn.className = "page-btn prev-btn";
  prevBtn.textContent = "◀ Previous";

  const pageInfo = document.createElement("span");
  pageInfo.className = "page-info";

  const nextBtn = document.createElement("button");
  nextBtn.type = "button";
  nextBtn.className = "page-btn next-btn";
  nextBtn.textContent = "Next ▶";

  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderPage(currentPage);
      scrollWrap.scrollTo({left: 0, behavior: "smooth"});
      wrapper.scrollIntoView({behavior: "smooth", block: "nearest"});
    }
  });

  nextBtn.addEventListener("click", () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderPage(currentPage);
      scrollWrap.scrollTo({left: 0, behavior: "smooth"});
      wrapper.scrollIntoView({behavior: "smooth", block: "nearest"});
    }
  });

  function setRowExpanded(sRow, dRow, chevron, moreBtn, totalCourses, expand) {
    if (expand) {
      sRow.classList.add("expanded");
      sRow.setAttribute("aria-expanded", "true");
      if (dRow) dRow.style.display = "table-row";
      if (chevron) chevron.textContent = "⌄";
      if (moreBtn && totalCourses > 2) {
        moreBtn.textContent = "Show less ▴";
        moreBtn.classList.add("is-open");
      }
    } else {
      sRow.classList.remove("expanded");
      sRow.setAttribute("aria-expanded", "false");
      if (dRow) dRow.style.display = "none";
      if (chevron) chevron.textContent = "›";
      if (moreBtn && totalCourses > 2) {
        moreBtn.textContent = `+${totalCourses - 2} more ▾`;
        moreBtn.classList.remove("is-open");
      }
    }
  }

  function renderPage(page) {
    body.innerHTML = "";
    const startIdx = (page - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalRows);
    const pageRows = rows.slice(startIdx, endIdx);

    if (isRank) {
      if (totalMatching > totalRows) {
        metaLabel.innerHTML = `Showing top <strong>${totalRows}</strong> of <strong>${totalMatching.toLocaleString()}</strong> matching students`;
      } else {
        metaLabel.innerHTML = `Showing all <strong>${totalRows}</strong> matching students. Only ${totalRows} students satisfy the selected conditions.`;
      }
    } else {
      if (totalRows > pageSize) {
        metaLabel.innerHTML = `Showing <strong>${startIdx + 1}–${endIdx}</strong> of <strong>${totalRows.toLocaleString()}</strong> matching students`;
      } else {
        metaLabel.innerHTML = `Showing all <strong>${totalRows.toLocaleString()}</strong> matching students`;
      }
    }

    pageRows.forEach((row, idx) => {
      const rankNum = startIdx + idx + 1;
      const rawCoursesVal = row.cleared_courses || row.attempted_courses || "";
      const coursesList = rawCoursesVal
        ? String(rawCoursesVal).split(", ").map(s => s.trim()).filter(Boolean)
        : [];
      const isExpandable = coursesList.length > 0;

      const tableRow = document.createElement("tr");
      tableRow.className = "student-row" + (isExpandable ? " expandable" : "");
      tableRow.dataset.courseCount = coursesList.length;

      // Detail row for expandable courses
      let detailRow = null;
      let chevron = null;
      let moreBtn = null;

      if (isExpandable) {
        detailRow = document.createElement("tr");
        detailRow.className = "student-detail-row";
        detailRow.style.display = "none";
        const totalCols = organizedColumns.length + (addRank ? 1 : 0);
        const detailCell = document.createElement("td");
        detailCell.colSpan = totalCols;

        const panel = document.createElement("div");
        panel.className = "student-detail-panel";

        const panelHeader = document.createElement("div");
        panelHeader.className = "detail-panel-header";

        const studentInfo = document.createElement("div");
        studentInfo.className = "detail-student-info";
        studentInfo.innerHTML = `
          <strong>${escapeHtml(row.name || "Student")}</strong>
          ${row.roll_number ? `<span class="detail-roll">${escapeHtml(row.roll_number)}</span>` : ""}
          ${row.department ? `<span>· ${escapeHtml(row.department)}</span>` : ""}
          <span class="detail-badge-count">✦ ${coursesList.length} ${row.attempted_courses ? "Attempted" : "Completed"}</span>
        `;

        const collapseBtn = document.createElement("button");
        collapseBtn.type = "button";
        collapseBtn.className = "detail-collapse-btn";
        collapseBtn.textContent = "✕ Close";

        panelHeader.append(studentInfo, collapseBtn);

        const coursesContainer = document.createElement("div");
        coursesContainer.className = "detail-courses-list";
        coursesList.forEach(courseStr => {
          const card = document.createElement("div");
          card.className = "detail-course-card";
          card.innerHTML = `<span class="detail-course-check">✓</span><span>${escapeHtml(courseStr)}</span>`;
          coursesContainer.appendChild(card);
        });

        panel.append(panelHeader, coursesContainer);
        detailCell.appendChild(panel);
        detailRow.appendChild(detailCell);

        collapseBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          setRowExpanded(tableRow, detailRow, chevron, moreBtn, coursesList.length, false);
        });
      }

      // Rank Cell
      if (addRank) {
        const rankCell = document.createElement("td");
        rankCell.className = "td-rank";
        const rankWrap = document.createElement("div");
        rankWrap.className = "rank-wrap";

        if (isExpandable) {
          chevron = document.createElement("span");
          chevron.className = "row-chevron";
          chevron.textContent = "›";
          rankWrap.appendChild(chevron);
        }

        const rankBadge = document.createElement("span");
        rankBadge.className = "rank-badge" + (isRank && rankNum <= 3 ? ` rank-${rankNum}` : "");
        rankBadge.textContent = String(rankNum);
        rankWrap.appendChild(rankBadge);

        rankCell.appendChild(rankWrap);
        tableRow.appendChild(rankCell);
      }

      // Column Cells
      organizedColumns.forEach((column) => {
        const cell = document.createElement("td");
        cell.className = getColumnClass("td", column);
        const val = row[column] ?? "";

        if ((column === "cleared_courses" || column === "attempted_courses") && val) {
          const wrap = document.createElement("div");
          wrap.className = "courses-cell";

          const previewCount = 2;
          const previewList = coursesList.slice(0, previewCount);
          previewList.forEach(c => {
            wrap.appendChild(createCourseBadge(c));
          });

          if (coursesList.length > previewCount) {
            moreBtn = document.createElement("button");
            moreBtn.type = "button";
            moreBtn.className = "course-more-pill";
            moreBtn.textContent = `+${coursesList.length - previewCount} more ▾`;
            moreBtn.title = `View all ${coursesList.length} courses`;
            moreBtn.addEventListener("click", (e) => {
              e.stopPropagation();
              const isCurrentlyExpanded = tableRow.classList.contains("expanded");
              setRowExpanded(tableRow, detailRow, chevron, moreBtn, coursesList.length, !isCurrentlyExpanded);
            });
            wrap.appendChild(moreBtn);
          }

          cell.appendChild(wrap);
        } else if (column === "roll_number" && val) {
          const badge = document.createElement("span");
          badge.className = "roll-badge";
          badge.textContent = val;
          cell.appendChild(badge);
        } else if (column === "name" && val) {
          const nameEl = document.createElement("span");
          nameEl.className = "student-name";
          nameEl.textContent = val;
          cell.appendChild(nameEl);
        } else if (column === "dept_code" && val) {
          const pill = document.createElement("span");
          pill.className = "dept-pill";
          pill.textContent = val;
          cell.appendChild(pill);
        } else if (column === "department" && val) {
          const dept = document.createElement("span");
          dept.className = "dept-name";
          dept.textContent = val;
          dept.title = val;
          cell.appendChild(dept);
        } else if ((column === "completed_levels" || column === "total_levels_cleared") && val) {
          const pill = document.createElement("span");
          pill.className = "levels-pill";
          const countNum = Number(val) || val;
          pill.innerHTML = `<strong>${countNum}</strong> ${countNum === 1 ? "Level" : "Levels"}`;
          cell.appendChild(pill);
        } else if (column === "status" && val) {
          const pill = document.createElement("span");
          const sLower = String(val).toLowerCase();
          const statusClass = sLower.includes("clear") && !sLower.includes("not") ? "status-cleared"
            : sLower.includes("pending") ? "status-pending" : "status-failed";
          pill.className = `status-pill ${statusClass}`;
          pill.textContent = val;
          cell.appendChild(pill);
        } else {
          cell.textContent = val !== null && val !== undefined && val !== "" ? val : "—";
        }

        tableRow.appendChild(cell);
      });

      // Expandable toggle on row click
      if (isExpandable) {
        tableRow.addEventListener("click", () => {
          const isCurrentlyExpanded = tableRow.classList.contains("expanded");
          setRowExpanded(tableRow, detailRow, chevron, moreBtn, coursesList.length, !isCurrentlyExpanded);
        });
      }

      body.appendChild(tableRow);
      if (detailRow) {
        body.appendChild(detailRow);
      }
    });

    pageInfo.textContent = `Page ${page} of ${totalPages}`;
    prevBtn.disabled = page === 1;
    nextBtn.disabled = page === totalPages;
  }

  // Toggle All Button Listener
  if (toggleAllBtn) {
    toggleAllBtn.addEventListener("click", () => {
      allExpanded = !allExpanded;
      toggleAllBtn.innerHTML = allExpanded ? `<span>Collapse All</span> ▴` : `<span>Expand All</span> ▾`;

      const studentRows = body.querySelectorAll("tr.student-row");
      const detailRows = body.querySelectorAll("tr.student-detail-row");

      studentRows.forEach((sRow, idx) => {
        const dRow = detailRows[idx];
        const chevron = sRow.querySelector(".row-chevron");
        const moreBtn = sRow.querySelector(".course-more-pill");
        const count = Number(sRow.dataset.courseCount || 0);
        if (count > 0) {
          setRowExpanded(sRow, dRow, chevron, moreBtn, count, allExpanded);
        }
      });
    });
  }

  // Initial render of page 1
  renderPage(1);
  table.append(head, body);
  scrollWrap.appendChild(table);

  // 3. PINNED ACTIONS BAR
  const actions = document.createElement("div");
  actions.className = "table-actions";

  const exportGroup = document.createElement("div");
  exportGroup.className = "table-export-group";

  const csvButton = document.createElement("button");
  csvButton.type = "button";
  csvButton.className = "table-action csv-btn";
  csvButton.textContent = totalRows > 1 ? `↓ Download CSV (${totalRows} students)` : "↓ Download CSV";
  csvButton.addEventListener("click", () => downloadCsv(organizedColumns, rows));

  const sheetsButton = document.createElement("button");
  sheetsButton.type = "button";
  sheetsButton.className = "table-action sheets-btn";
  sheetsButton.textContent = totalRows > 1 ? `▣ Copy for Google Sheets (${totalRows} students)` : "▣ Copy for Google Sheets";
  sheetsButton.addEventListener("click", async () => {
    const headerLabels = organizedColumns.map(formatColumnHeader);
    const tsv = [
      headerLabels.join("\t"),
      ...rows.map((row) => organizedColumns.map((column) => (row[column] ?? "").toString().replace(/[\t\n\r]/g, " ")).join("\t"))
    ].join("\n");

    let copied = false;
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        await navigator.clipboard.writeText(tsv);
        copied = true;
      } catch {
        // Fallback to execCommand if clipboard API throws
      }
    }

    if (!copied) {
      try {
        const textarea = document.createElement("textarea");
        textarea.value = tsv;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        copied = true;
      } catch (err) {
        console.warn("Clipboard fallback copy failed:", err);
      }
    }

    if (copied) {
      sheetsButton.textContent = "✓ Copied all students — paste into Google Sheets";
      setTimeout(() => { 
        sheetsButton.textContent = totalRows > 1 ? `▣ Copy for Google Sheets (${totalRows} students)` : "▣ Copy for Google Sheets"; 
      }, 2500);
    }
  });

  exportGroup.append(csvButton, sheetsButton);
  actions.appendChild(exportGroup);

  if (totalRows > pageSize) {
    const paginator = document.createElement("div");
    paginator.className = "table-pagination";
    paginator.append(prevBtn, pageInfo, nextBtn);
    actions.appendChild(paginator);
  }

  wrapper.append(topBar, scrollWrap, actions);
  return wrapper;
}

function downloadCsv(columns, rows) {
  const escape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const headers = columns.map(formatColumnHeader);
  const csv = [
    headers.map(escape).join(","),
    ...rows.map((row) => columns.map((column) => escape(row[column])).join(","))
  ].join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], {type: "text/csv;charset=utf-8"}));
  link.download = "skillquery-student-results.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}

function renderAnswer(element, text, hasOptions) {
  const optionLine = /^\s*\*?\d+\*?\s*[-.)]\s*.+$/;
  const lines = text.split("\n").filter((line) => !hasOptions || !optionLine.test(line));
  const cleaned = lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();

  // Parse markdown bold and italic formatting
  const p = document.createElement("div");
  const formatted = cleaned
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
  p.innerHTML = formatted;
  element.appendChild(p);
}

function extractOptions(text) {
  if (!/select|which|option|matching topic|level/i.test(text)) return [];
  return text.split("\n").flatMap((line) => {
    const match = line.match(/^\s*\*?(\d+)\*?\s*[-.)]\s*(.+?)\s*$/);
    return match ? [{number: Number(match[1]), label: match[2].replace(/\*/g, "").trim()}] : [];
  });
}

question.addEventListener("input", () => {
  charCount.textContent = `${question.value.length} / 1000`;
});

document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => {
    question.value = button.dataset.question;
    question.dispatchEvent(new Event("input"));
    question.focus();
  });
});

question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;
  addMessage("user", text);
  content.classList.add("has-chat");
  submit.disabled = true;
  submit.querySelector("span:first-child").textContent = "Analyzing…";
  answerSection.classList.remove("hidden");
  const loading = document.createElement("div");
  loading.className = "chat-message assistant loading";
  loading.textContent = "Searching verified student records…";
  chat.appendChild(loading);
  try {
    const response = await fetch("/api/query", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: text, session_id: sessionId}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed.");
    loading.remove();
    addMessage("assistant", data.answer, extractOptions(data.answer), data);
    question.value = "";
    question.dispatchEvent(new Event("input"));
  } catch (error) {
    loading.remove();
    addMessage("assistant", error.message || "Something went wrong. Please try again.");
  } finally {
    submit.disabled = false;
    submit.querySelector("span:first-child").textContent = "Ask SkillQuery";
  }
});

clearButton.addEventListener("click", async () => {
  chat.innerHTML = "";
  content.classList.remove("has-chat");
  answerSection.classList.add("hidden");
  try {
    await fetch("/api/reset", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({session_id: sessionId})
    });
  } catch (e) {
    console.warn("Failed to reset session on server:", e);
  }
});
