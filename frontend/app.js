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
    const content = document.createElement("div");
    content.className = "answer";

    // Always render textual summary and explanations
    renderAnswer(content, text, options.length > 0);
    body.append(label, content);

    // If metadata contains included courses description, render explanation note
    if (tableData && tableData.meta && tableData.meta.description) {
      const note = document.createElement("div");
      note.className = "taxonomy-note";
      note.style.fontSize = "0.82rem";
      note.style.color = "var(--text-muted, #8e8ea0)";
      note.style.margin = "6px 0 10px 0";
      note.innerHTML = `<strong>Domain Scope:</strong> ${tableData.meta.description}`;
      body.appendChild(note);
    }

    const hasStudentTable = tableData && tableData.rows && tableData.rows.length
      && tableData.columns && tableData.columns.some(c => ["name", "roll_number", "student_count"].includes(c));

    if (hasStudentTable) {
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
        option.innerHTML = `<span>${number}</span>${optionLabel}`;
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

  // Top bar with count messaging
  const topBar = document.createElement("div");
  topBar.className = "table-meta-bar";
  const metaLabel = document.createElement("span");
  metaLabel.className = "table-count-label";
  topBar.appendChild(metaLabel);

  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");

  // Add Rank column if multiple rows
  const addRank = totalRows > 1;
  if (addRank) {
    const rankHeader = document.createElement("th");
    rankHeader.textContent = "#";
    headerRow.appendChild(rankHeader);
  }

  columns.forEach((column) => {
    const cell = document.createElement("th");
    if (column === "cleared_courses") {
      cell.textContent = "Courses / Levels Cleared";
    } else if (column === "attempted_courses") {
      cell.textContent = "Attempted Courses";
    } else if (column === "completed_levels") {
      cell.textContent = "Completed Levels";
    } else {
      cell.textContent = column.replaceAll("_", " ");
    }
    headerRow.appendChild(cell);
  });
  head.appendChild(headerRow);
  const body = document.createElement("tbody");

  // Pagination controls elements
  const prevBtn = document.createElement("button");
  prevBtn.type = "button";
  prevBtn.className = "page-btn";
  prevBtn.textContent = "◀ Previous";

  const pageInfo = document.createElement("span");
  pageInfo.className = "page-info";

  const nextBtn = document.createElement("button");
  nextBtn.type = "button";
  nextBtn.className = "page-btn";
  nextBtn.textContent = "Next ▶";

  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage--;
      renderPage(currentPage);
    }
  });

  nextBtn.addEventListener("click", () => {
    if (currentPage < totalPages) {
      currentPage++;
      renderPage(currentPage);
    }
  });

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
      const tableRow = document.createElement("tr");
      if (addRank) {
        const rankCell = document.createElement("td");
        rankCell.textContent = String(startIdx + idx + 1);
        rankCell.style.fontWeight = "600";
        rankCell.style.color = "var(--text-muted, #8e8ea0)";
        tableRow.appendChild(rankCell);
      }
      columns.forEach((column) => {
        const cell = document.createElement("td");
        const val = row[column] ?? "";
        if ((column === "cleared_courses" || column === "attempted_courses") && val) {
          const wrap = document.createElement("div");
          wrap.className = "courses-cell";
          const courses = String(val).split(", ");
          wrap.innerHTML = courses
            .map(c => `<span class="course-pill">${c}</span>`)
            .join("");
          cell.appendChild(wrap);
        } else {
          cell.textContent = val;
        }
        tableRow.appendChild(cell);
      });
      body.appendChild(tableRow);
    });

    pageInfo.textContent = `Page ${page} of ${totalPages}`;
    prevBtn.disabled = page === 1;
    nextBtn.disabled = page === totalPages;
  }

  // Initial render of page 1
  renderPage(1);
  table.append(head, body);

  const actions = document.createElement("div");
  actions.className = "table-actions";

  const csvButton = document.createElement("button");
  csvButton.type = "button";
  csvButton.className = "table-action";
  csvButton.textContent = totalRows > 1 ? `↓ Download CSV (${totalRows} students)` : "↓ Download CSV";
  csvButton.addEventListener("click", () => downloadCsv(columns, rows));

  const sheetsButton = document.createElement("button");
  sheetsButton.type = "button";
  sheetsButton.className = "table-action";
  sheetsButton.textContent = totalRows > 1 ? `▣ Copy for Google Sheets (${totalRows} students)` : "▣ Copy for Google Sheets";
  sheetsButton.addEventListener("click", async () => {
    const tsv = [columns.join("\t"), ...rows.map((row) => columns.map((column) => row[column] ?? "").join("\t"))].join("\n");
    await navigator.clipboard.writeText(tsv);
    sheetsButton.textContent = "✓ Copied all students — paste into Google Sheets";
    setTimeout(() => { 
      sheetsButton.textContent = totalRows > 1 ? `▣ Copy for Google Sheets (${totalRows} students)` : "▣ Copy for Google Sheets"; 
    }, 2500);
  });

  actions.append(csvButton, sheetsButton);

  if (totalRows > pageSize) {
    const paginator = document.createElement("div");
    paginator.className = "table-pagination";
    paginator.append(prevBtn, pageInfo, nextBtn);
    actions.appendChild(paginator);
  }

  wrapper.append(topBar, table, actions);
  return wrapper;
}

function downloadCsv(columns, rows) {
  const escape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [columns.map(escape).join(","), ...rows.map((row) => columns.map((column) => escape(row[column])).join(","))].join("\n");
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
