"use client";
 
import { useMemo, useState } from "react";
 
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
 
const GA_CONFIG = {
  population_size: 10,
  generations: 20,
  mutation_rate: 0.05,
  crossover_rate: 0.8,
  elite_size: 5,
  tournament_size: 3,
  seed: 42,
};
 
const GA_PARAMS = [
  { key: "population_size", label: "Quy mô quần thể" },
  { key: "generations", label: "Số thế hệ" },
  { key: "mutation_rate", label: "Tỷ lệ đột biến" },
  { key: "crossover_rate", label: "Tỷ lệ lai ghép" },
  { key: "elite_size", label: "Số cá thể ưu tú" },
  { key: "tournament_size", label: "Kích thước giải đấu" },
];
 
const DATASETS = [
  { id: "small", name: "Nhỏ", detail: "8 lớp, 12 học phần, 8 giảng viên" },
  { id: "medium", name: "Trung bình", detail: "20 lớp, 42 học phần, 28 giảng viên" },
  { id: "large", name: "Lớn", detail: "50 lớp, 125 học phần, 45 giảng viên" },
];
 
const ALGORITHMS = [
  {
    id: "genetic",
    name: "Thuật toán di truyền",
    short: "Di truyền (GA)",
    detail: "Tiến hóa quần thể lịch qua lai ghép và đột biến.",
  },
  {
    id: "greedy",
    name: "Thuật toán tham lam",
    short: "Tham lam",
    detail: "Xếp lần lượt từng học phần vào chỗ tốt nhất lúc đó.",
  },
  {
    id: "random",
    name: "Ngẫu nhiên",
    short: "Ngẫu nhiên",
    detail: "Chọn chỗ ngẫu nhiên, dùng làm mốc so sánh.",
  },
];
 
const datasetById = Object.fromEntries(DATASETS.map((d) => [d.id, d]));
const algorithmById = Object.fromEntries(ALGORITHMS.map((a) => [a.id, a]));
 
const DAYS = [
  { id: 0, name: "Thứ 2" },
  { id: 1, name: "Thứ 3" },
  { id: 2, name: "Thứ 4" },
  { id: 3, name: "Thứ 5" },
  { id: 4, name: "Thứ 6" },
  { id: 5, name: "Thứ 7" },
];
 
const PERIODS = Array.from({ length: 10 }, (_, i) => i + 1);
 
const VIEW_MODES = {
  class_id: { label: "Lớp", title: "Lớp" },
  teacher_id: { label: "Giảng viên", title: "Giảng viên" },
  room_id: { label: "Phòng", title: "Phòng" },
};
 
const CONSTRAINTS = {
  saturday_afternoon: ["Thứ 7 buổi chiều", "Không xếp lịch sau tiết 5 ngày thứ 7."],
  invalid_timeslot: ["Khung giờ không hợp lệ", "Học phần phải nằm trong tiết 1–10."],
  room_capacity: ["Sức chứa phòng", "Phòng phải đủ chỗ cho sĩ số lớp."],
  missing_room: ["Phòng không tồn tại", "Mã phòng không có trong dữ liệu."],
  room_type: ["Loại phòng", "Học phần thực hành phải ở phòng máy (LAB)."],
  teacher_availability: ["Lịch rảnh giảng viên", "Không xếp vào giờ giảng viên bận."],
  teacher_conflict: ["Trùng giảng viên", "Một giảng viên dạy hai nơi cùng lúc."],
  class_conflict: ["Trùng lớp", "Một lớp học hai học phần cùng lúc."],
  room_conflict: ["Trùng phòng", "Hai học phần dùng chung phòng cùng lúc."],
  student_daily_overload: ["Lớp vượt 8 tiết/ngày", "Mỗi lớp học tối đa 8 tiết một ngày."],
  teacher_daily_overload: ["Giảng viên vượt tải/ngày", "Vượt số tiết tối đa giảng viên dạy trong ngày."],
  preferred_day: ["Đúng ngày ưu tiên", "+2 cho mỗi học phần rơi vào ngày mong muốn."],
  preferred_period: ["Đúng tiết ưu tiên", "+1 cho mỗi học phần bắt đầu ở tiết mong muốn."],
  preferred_day_missed: ["Trượt ngày ưu tiên", "Học phần không rơi vào ngày mong muốn."],
  preferred_period_missed: ["Trượt tiết ưu tiên", "Học phần không bắt đầu ở tiết mong muốn."],
  teacher_preference: ["Ngày ưu tiên giảng viên", "Giảng viên phải dạy vào ngày không mong muốn."],
  student_gaps: ["Khoảng trống của lớp", "Số quãng nghỉ giữa các tiết trong ngày."],
  daily_balance: ["Cân bằng tải theo ngày", "Chênh lệch số tiết giữa ngày nặng nhất và nhẹ nhất."],
  avoid_same_day: ["Môn tránh cùng ngày", "Hai môn nên tách ngày lại bị xếp chung."],
};
 
// "C2" < "C10" (natural sort for ids like C1, T12, LAB3).
const naturalCompare = (a, b) => a.localeCompare(b, undefined, { numeric: true });
 
const formatMs = (ms) =>
  ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`;
 
async function requestTimetable(dataset, algorithm) {
  let response;
 
  try {
    response = await fetch(`${API}/timetables/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, algorithm, ...GA_CONFIG }),
    });
  } catch {
    throw new Error(
      `Không kết nối được tới máy chủ tại ${API}. Hãy chạy backend bằng lệnh "uvicorn app.main:app --reload" trong thư mục backend rồi thử lại.`,
    );
  }
 
  const data = await response.json().catch(() => ({}));
 
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d) => d.msg).join("; ")
      : data.detail;
    throw new Error(detail || `Máy chủ trả về lỗi HTTP ${response.status}.`);
  }
 
  return data;
}
 
/**
 * Splits blocks of one day into side-by-side lanes when they overlap
 * (only happens when hard constraints are violated, e.g. Random).
 */
function layoutDay(blocks) {
  const sorted = [...blocks].sort((a, b) => a.start - b.start);
  const placed = [];
  let cluster = [];
  let clusterEnd = -1;
 
  const flush = () => {
    const laneEnds = [];
    cluster.forEach((block) => {
      let lane = laneEnds.findIndex((end) => end <= block.start);
      if (lane === -1) lane = laneEnds.length;
      laneEnds[lane] = block.end;
      block.lane = lane;
    });
    cluster.forEach((block) => {
      block.lanes = laneEnds.length;
      placed.push(block);
    });
    cluster = [];
  };
 
  sorted.forEach((block) => {
    if (cluster.length && block.start >= clusterEnd) flush();
    cluster.push(block);
    clusterEnd = Math.max(clusterEnd, block.end);
  });
  if (cluster.length) flush();
 
  return placed;
}
 
/** True when two lessons in the list share a day and overlapping periods. */
function hasOverlap(items) {
  const byDay = {};
  for (const a of items) {
    const start = a.start_period;
    const end = start + (a.duration || 1);
    for (const [s, e] of byDay[a.day] || []) {
      if (start < e && s < end) return true;
    }
    (byDay[a.day] ||= []).push([start, end]);
  }
  return false;
}
 
export default function Home() {
  const [dataset, setDataset] = useState("medium");
  const [algorithm, setAlgorithm] = useState("genetic");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [viewMode, setViewMode] = useState("class_id");
  const [viewTarget, setViewTarget] = useState("");
  const [comparison, setComparison] = useState(null);
  const [comparing, setComparing] = useState(false);
  const [compareError, setCompareError] = useState("");
 
  const busy = loading || comparing;
 
  async function generate() {
    setLoading(true);
    setError("");
 
    try {
      const data = await requestTimetable(dataset, algorithm);
      setResult(data);
      setViewTarget("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
 
  async function compare() {
    setComparing(true);
    setCompareError("");
 
    try {
      const rows = [];
      for (const algo of ALGORITHMS) {
        const data = await requestTimetable(dataset, algo.id);
        rows.push({
          algorithm: algo.id,
          fitness: data.fitness,
          runtime_ms: data.runtime_ms,
        });
      }
      setComparison({ dataset, rows });
    } catch (e) {
      setCompareError(e.message);
    } finally {
      setComparing(false);
    }
  }
 
  const history = result?.history || [];
  const assignments = result?.assignments || [];
 
  const viewOptions = useMemo(
    () => [...new Set(assignments.map((a) => a[viewMode]))].sort(naturalCompare),
    [assignments, viewMode],
  );
 
  const activeTarget = viewOptions.includes(viewTarget)
    ? viewTarget
    : viewOptions[0] || "";
 
  const visibleBlocks = useMemo(() => {
    const filtered = assignments
      .filter((a) => a[viewMode] === activeTarget)
      .map((a) => ({
        ...a,
        start: a.start_period,
        end: a.start_period + (a.duration || 1),
      }));
 
    return DAYS.flatMap((day) =>
      layoutDay(filtered.filter((a) => a.day === day.id)),
    );
  }, [assignments, viewMode, activeTarget]);
 
  const overlapCount = visibleBlocks.filter((block) => block.lanes > 1).length;
 
  // Per-option summary for the picker: how many lessons, and whether any overlap.
  const optionStats = useMemo(() => {
    const stats = {};
    viewOptions.forEach((option) => {
      const items = assignments.filter((a) => a[viewMode] === option);
      stats[option] = { count: items.length, conflict: hasOverlap(items) };
    });
    return stats;
  }, [assignments, viewMode, viewOptions]);
 
  const conflictedOptions = viewOptions.filter((o) => optionStats[o]?.conflict);
  const targetIndex = viewOptions.indexOf(activeTarget);
 
  const stepTarget = (delta) => {
    if (!viewOptions.length) return;
    const next = (targetIndex + delta + viewOptions.length) % viewOptions.length;
    setViewTarget(viewOptions[next]);
  };
 
  const steps = [
    {
      href: "#cau-hinh",
      title: "Cấu hình tối ưu",
      status: `${datasetById[dataset].name}, ${algorithmById[algorithm].short}`,
      done: true,
    },
    {
      href: "#ket-qua",
      title: "Kết quả chạy",
      status: result
        ? `${result.fitness.hard_violations} vi phạm, ${result.fitness.soft_penalty} điểm phạt`
        : "Chưa chạy",
      done: Boolean(result),
    },
    {
      href: "#thoi-khoa-bieu",
      title: "Thời khóa biểu",
      status: result
        ? `${assignments.length} học phần đã xếp`
        : "Xem theo lớp, giảng viên, phòng",
      done: Boolean(result),
    },
    {
      href: "#so-sanh",
      title: "So sánh thuật toán",
      status: comparison
        ? `Đã so sánh trên bộ ${datasetById[comparison.dataset].name}`
        : "GA, tham lam, ngẫu nhiên",
      done: Boolean(comparison),
    },
  ];
 
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <BrandMark />
          <div>
            <strong>GA Timetable</strong>
            <span>Lập thời khóa biểu thông minh</span>
          </div>
        </div>
        <span className="topbar-note">Nhóm 5, Phân tích và thiết kế thuật toán</span>
      </header>
 
      <main className="page">
        <section className="welcome">
          <div className="welcome-text">
            <h1>Chào mừng bạn!</h1>
            <p>
              Tạo thời khóa biểu phù hợp với các ràng buộc của trường: không trùng
              giảng viên, lớp hay phòng, đúng lịch rảnh, và đáp ứng tối đa ngày,
              tiết mà mỗi học phần mong muốn.
            </p>
          </div>
 
          <ol className="steps">
            {steps.map((step, index) => (
              <li key={step.href}>
                <a href={step.href} className={`step ${step.done ? "done" : ""}`}>
                  <span className="step-number" aria-hidden="true">
                    {step.done && index > 0 ? "✓" : index + 1}
                  </span>
                  <span className="step-text">
                    <strong>{step.title}</strong>
                    <small>{step.status}</small>
                  </span>
                </a>
              </li>
            ))}
          </ol>
        </section>
 
        <section id="cau-hinh" className="card config">
          <div className="card-head">
            <div>
              <h2>Cấu hình tối ưu</h2>
              <p>Chọn bộ dữ liệu và thuật toán, rồi tạo thời khóa biểu.</p>
            </div>
          </div>
 
          <div className="config-grid">
            <fieldset className="choice-group" disabled={busy}>
              <legend>Bộ dữ liệu</legend>
              <div className="choices">
                {DATASETS.map((d) => (
                  <label
                    key={d.id}
                    className={`choice ${dataset === d.id ? "selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="dataset"
                      value={d.id}
                      checked={dataset === d.id}
                      onChange={() => setDataset(d.id)}
                    />
                    <strong>{d.name}</strong>
                    <small>{d.detail}</small>
                  </label>
                ))}
              </div>
            </fieldset>
 
            <fieldset className="choice-group" disabled={busy}>
              <legend>Thuật toán</legend>
              <div className="choices">
                {ALGORITHMS.map((a) => (
                  <label
                    key={a.id}
                    className={`choice ${algorithm === a.id ? "selected" : ""}`}
                  >
                    <input
                      type="radio"
                      name="algorithm"
                      value={a.id}
                      checked={algorithm === a.id}
                      onChange={() => setAlgorithm(a.id)}
                    />
                    <strong>{a.name}</strong>
                    <small>{a.detail}</small>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
 
          <div className="config-foot">
            <dl className={`params ${algorithm === "genetic" ? "" : "muted"}`}>
              {GA_PARAMS.map((p) => (
                <div key={p.key}>
                  <dt>{p.label}</dt>
                  <dd>{GA_CONFIG[p.key]}</dd>
                </div>
              ))}
            </dl>
 
            <button className="btn-primary" onClick={generate} disabled={busy}>
              {loading ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Đang tạo thời khóa biểu…
                </>
              ) : (
                "Tạo thời khóa biểu"
              )}
            </button>
          </div>
          {algorithm !== "genetic" && (
            <p className="hint">Tham số trên chỉ áp dụng cho thuật toán di truyền.</p>
          )}
        </section>
 
        {error && (
          <div className="alert" role="alert">
            <div>
              <strong>Chưa tạo được thời khóa biểu.</strong>
              <span>{error}</span>
            </div>
            <button type="button" className="btn-ghost" onClick={generate} disabled={busy}>
              Thử lại
            </button>
          </div>
        )}
 
        <section
          id="ket-qua"
          className={`card results ${loading && result ? "stale" : ""}`}
          aria-busy={loading}
        >
          <div className="card-head">
            <div>
              <h2>Kết quả tối ưu hóa</h2>
              <p>
                {result
                  ? `${algorithmById[result.algorithm].name} trên bộ dữ liệu ${
                      datasetById[result.dataset]?.name || result.dataset
                    }.`
                  : "Chỉ số, biểu đồ hội tụ và báo cáo ràng buộc sẽ hiện ở đây sau khi chạy."}
              </p>
            </div>
            {result && (
              <span className={`pill ${result.fitness.hard_violations === 0 ? "ok" : "bad"}`}>
                {result.fitness.hard_violations === 0
                  ? "Lịch hợp lệ"
                  : "Lịch còn vi phạm ràng buộc cứng"}
              </span>
            )}
          </div>
 
          {!result && loading && (
            <div className="placeholder">
              <span className="spinner dark" aria-hidden="true" />
              Đang chạy {algorithmById[algorithm].name.toLowerCase()} trên bộ dữ liệu{" "}
              {datasetById[dataset].name.toLowerCase()}. Bộ lớn có thể mất vài giây.
            </div>
          )}
 
          {!result && !loading && (
            <div className="placeholder">
              Chưa có kết quả. Bấm <strong>Tạo thời khóa biểu</strong> ở trên để bắt đầu.
            </div>
          )}
 
          {result && (
            <>
              <div className="metrics">
                <Metric
                  label="Vi phạm ràng buộc cứng"
                  value={result.fitness.hard_violations}
                  note="Phải bằng 0 để lịch dùng được"
                  tone={result.fitness.hard_violations === 0 ? "ok" : "bad"}
                />
                <Metric
                  label="Điểm phạt ràng buộc mềm"
                  value={result.fitness.soft_penalty}
                  note="Càng thấp càng tốt"
                />
                <Metric
                  label="Điểm thưởng ưu tiên"
                  value={result.fitness.preference_reward}
                  note="Càng cao càng tốt"
                />
                <Metric
                  label="Thời gian chạy"
                  value={formatMs(result.runtime_ms)}
                  note={`${assignments.length} học phần`}
                />
              </div>
 
              <div className="results-grid">
                <div className="sub-card">
                  <div className="sub-head">
                    <h3>Lịch sử hội tụ</h3>
                    <span>
                      {history.length > 0
                        ? `Điểm phạt mềm tốt nhất qua ${history.length - 1} thế hệ`
                        : ""}
                    </span>
                  </div>
                  {history.length > 0 ? (
                    <ConvergenceChart history={history} />
                  ) : (
                    <div className="placeholder small">
                      {algorithmById[result.algorithm].name} chạy một lượt nên không
                      có lịch sử hội tụ. Chọn thuật toán di truyền để xem biểu đồ.
                    </div>
                  )}
                </div>
 
                <div className="sub-card">
                  <div className="sub-head">
                    <h3>Báo cáo ràng buộc</h3>
                    <span>Chi tiết từng quy tắc</span>
                  </div>
                  <ConstraintGroup
                    title="Ràng buộc cứng"
                    type="hard"
                    data={result.constraint_report?.hard || {}}
                    empty="Không có vi phạm"
                  />
                  <ConstraintGroup
                    title="Ràng buộc mềm"
                    type="soft"
                    data={result.constraint_report?.soft || {}}
                    empty="Không có điểm phạt"
                  />
                  <ConstraintGroup
                    title="Điểm thưởng ưu tiên"
                    type="reward"
                    data={result.constraint_report?.reward || {}}
                    empty="Chưa đạt ưu tiên nào"
                  />
                </div>
              </div>
            </>
          )}
        </section>
 
        <section id="thoi-khoa-bieu" className="card timetable-card">
          <div className="card-head">
            <div>
              <h2>Thời khóa biểu theo ngày</h2>
              <p>
                {result
                  ? `${VIEW_MODES[viewMode].title} ${activeTarget}: ${visibleBlocks.length} học phần trong tuần.`
                  : "Lịch sẽ hiện ở đây sau khi tạo. Có thể xem theo lớp, giảng viên hoặc phòng."}
              </p>
            </div>
          </div>
 
          {result ? (
            <>
              <div className="toolbar">
                <div className="segmented" role="group" aria-label="Xem theo">
                  {Object.entries(VIEW_MODES).map(([key, mode]) => (
                    <button
                      key={key}
                      aria-pressed={viewMode === key}
                      className={viewMode === key ? "active" : ""}
                      onClick={() => {
                        setViewMode(key);
                        setViewTarget("");
                      }}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
 
                <div className="target-picker">
                  <label className="target-select">
                    <span>Chọn {VIEW_MODES[viewMode].label.toLowerCase()}</span>
                    <select
                      value={activeTarget}
                      onChange={(e) => setViewTarget(e.target.value)}
                    >
                      {viewOptions.map((option) => (
                        <option key={option} value={option}>
                          {optionStats[option]?.conflict ? "⚠ " : ""}
                          {option} · {optionStats[option]?.count ?? 0} học phần
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="stepper" role="group" aria-label="Chuyển nhanh">
                    <button
                      type="button"
                      onClick={() => stepTarget(-1)}
                      aria-label={`${VIEW_MODES[viewMode].label} trước`}
                    >
                      ‹
                    </button>
                    <span>
                      {targetIndex + 1}/{viewOptions.length}
                    </span>
                    <button
                      type="button"
                      onClick={() => stepTarget(1)}
                      aria-label={`${VIEW_MODES[viewMode].label} kế tiếp`}
                    >
                      ›
                    </button>
                  </div>
                </div>
 
                <ul className="legend">
                  <li className="theory">Lý thuyết</li>
                  <li className="lab">Thực hành (phòng máy)</li>
                  <li className="off">Không xếp lịch</li>
                  {overlapCount > 0 && <li className="conflict">Trùng lịch</li>}
                </ul>
              </div>
 
              {overlapCount > 0 && (
                <p className="conflict-note">
                  {overlapCount} học phần đang bị trùng giờ. Chúng được đặt cạnh nhau
                  và viền đỏ để dễ nhận ra.
                </p>
              )}
 
              {conflictedOptions.length > 0 && (
                <div className="conflict-jump">
                  <span>
                    {conflictedOptions.length} {VIEW_MODES[viewMode].label.toLowerCase()} có
                    lịch trùng giờ:
                  </span>
                  <div className="chips">
                    {conflictedOptions.slice(0, 12).map((option) => (
                      <button
                        type="button"
                        key={option}
                        className={option === activeTarget ? "chip active" : "chip"}
                        aria-pressed={option === activeTarget}
                        onClick={() => setViewTarget(option)}
                      >
                        {option}
                      </button>
                    ))}
                    {conflictedOptions.length > 12 && (
                      <span className="chip more">
                        +{conflictedOptions.length - 12} (xem trong danh sách ⚠)
                      </span>
                    )}
                  </div>
                </div>
              )}
 
              <p className="scroll-hint">Vuốt ngang để xem các ngày còn lại →</p>
              <div className="timetable-scroll">
                <div className="timetable">
                  <div className="corner">Tiết</div>
 
                  {DAYS.map((day) => (
                    <div key={day.id} className="day-head">
                      <strong>{day.name}</strong>
                      {day.id === 5 && <small>Chỉ buổi sáng</small>}
                    </div>
                  ))}
 
                  {PERIODS.map((period) => (
                    <div
                      key={`time-${period}`}
                      className={`period ${period === 6 ? "pm-start" : ""}`}
                      style={{ gridColumn: 1, gridRow: period + 1 }}
                    >
                      <strong>{period}</strong>
                      <small>{period <= 5 ? "Sáng" : "Chiều"}</small>
                    </div>
                  ))}
 
                  {PERIODS.flatMap((period) =>
                    DAYS.map((day) => {
                      const off = day.id === 5 && period > 5;
                      return (
                        <div
                          key={`cell-${day.id}-${period}`}
                          className={`slot ${off ? "off" : ""} ${period === 6 ? "pm-start" : ""}`}
                          style={{ gridColumn: day.id + 2, gridRow: period + 1 }}
                        />
                      );
                    }),
                  )}
 
                  {visibleBlocks.map((block) => {
                    const duration = block.duration || 1;
                    const isLab = block.required_room_type === "LAB";
                    const width = 100 / block.lanes;
                    const split = block.lanes > 1;
 
                    return (
                      <article
                        key={`course-${block.course_offering_id}`}
                        className={`lesson ${isLab ? "lab" : "theory"} ${split ? "conflict" : ""}`}
                        style={{
                          gridColumn: block.day + 2,
                          gridRow: `${block.start_period + 1} / span ${duration}`,
                          width: split ? `calc(${width}% - 8px)` : undefined,
                          marginLeft: split ? `calc(${width * block.lane}% + 4px)` : undefined,
                        }}
                        title={`${block.course_code} – ${block.course_name}\nGiảng viên ${block.teacher_id}, lớp ${block.class_id}, phòng ${block.room_id}\nTiết ${block.start}–${block.end - 1}`}
                      >
                        <span className="lesson-time">
                          Tiết {block.start}–{block.end - 1}
                        </span>
                        <strong className="lesson-code">{block.course_code}</strong>
                        <span className="lesson-name">{block.course_name}</span>
                        <span className="lesson-meta">
                          {viewMode !== "teacher_id" && <span>GV {block.teacher_id}</span>}
                          {viewMode !== "class_id" && <span>Lớp {block.class_id}</span>}
                          {viewMode !== "room_id" && <span>Phòng {block.room_id}</span>}
                        </span>
                      </article>
                    );
                  })}
                </div>
              </div>
            </>
          ) : (
            <EmptyTimetable />
          )}
        </section>
 
        <section id="so-sanh" className="card compare">
          <div className="card-head">
            <div>
              <h2>So sánh thuật toán</h2>
              <p>
                Chạy cả ba thuật toán trên bộ dữ liệu{" "}
                {datasetById[dataset].name.toLowerCase()} với cùng tham số để so sánh
                chất lượng lịch và thời gian.
              </p>
            </div>
            <button className="btn-secondary" onClick={compare} disabled={busy}>
              {comparing ? (
                <>
                  <span className="spinner dark" aria-hidden="true" />
                  Đang so sánh…
                </>
              ) : comparison ? (
                "So sánh lại"
              ) : (
                "So sánh 3 thuật toán"
              )}
            </button>
          </div>
 
          {compareError && (
            <div className="alert" role="alert">
              <div>
                <strong>Chưa so sánh được.</strong>
                <span>{compareError}</span>
              </div>
              <button type="button" className="btn-ghost" onClick={compare} disabled={busy}>
                Thử lại
              </button>
            </div>
          )}
 
          {comparison ? (
            <ComparisonTable comparison={comparison} />
          ) : (
            !compareError && (
              <div className="placeholder">
                Chưa có dữ liệu so sánh. Bấm <strong>So sánh 3 thuật toán</strong> để
                chạy lần lượt di truyền, tham lam và ngẫu nhiên.
              </div>
            )
          )}
        </section>
      </main>
 
      <footer className="footer">
        Nhóm 5, Phân tích và thiết kế thuật toán. Máy chủ API: {API}
      </footer>
    </div>
  );
}
 
function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect x="1" y="1" width="30" height="30" rx="9" fill="var(--coral)" />
      <rect x="7" y="8" width="8" height="7" rx="2" fill="#fff" />
      <rect x="17" y="8" width="8" height="4" rx="2" fill="#fff" opacity=".55" />
      <rect x="7" y="17" width="8" height="4" rx="2" fill="#fff" opacity=".55" />
      <rect x="17" y="14" width="8" height="10" rx="2" fill="#fff" />
    </svg>
  );
}
 
function Metric({ label, value, note, tone = "" }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
 
function ConvergenceChart({ history }) {
  const values = history.map((h) => Number(h.soft_penalty) || 0);
  const gens = history.map((h, i) => h.generation ?? i);
  const first = values[0];
  const last = values[values.length - 1];
  const hardFirst = history[0]?.hard_violations;
  const hardLast = history[history.length - 1]?.hard_violations;
 
  // Scale the y axis to the real range so small improvements stay visible.
  const W = 640;
  const H = 240;
  const pad = { top: 22, right: 18, bottom: 30, left: 44 };
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || Math.max(Math.abs(hi) * 0.1, 1);
  const yMin = lo - span * 0.25;
  const yMax = hi + span * 0.25;
  const n = Math.max(values.length - 1, 1);
 
  const x = (i) => pad.left + (i / n) * (W - pad.left - pad.right);
  const y = (v) => pad.top + ((yMax - v) / (yMax - yMin)) * (H - pad.top - pad.bottom);
 
  // Best-so-far values change in steps, so draw a step line.
  let line = `M ${x(0)} ${y(values[0])}`;
  for (let i = 1; i < values.length; i += 1) {
    line += ` H ${x(i)} V ${y(values[i])}`;
  }
  const area = `${line} V ${H - pad.bottom} H ${x(0)} Z`;
 
  const ticks = [yMin + (yMax - yMin) * 0.15, (yMin + yMax) / 2, yMax - (yMax - yMin) * 0.15];
  const labelEvery = Math.ceil(values.length / 10);
  const changes = values
    .map((v, i) => ({ v, i }))
    .filter(({ v, i }) => i === 0 || i === values.length - 1 || v !== values[i - 1]);
  const fmt = (v) => (Number.isInteger(v) ? v : Number(v.toFixed(1)));
 
  return (
    <>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Điểm phạt mềm giảm từ ${first} xuống ${last} qua ${n} thế hệ`}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line className="chart-grid" x1={pad.left} x2={W - pad.right} y1={y(t)} y2={y(t)} />
            <text className="chart-axis" x={pad.left - 8} y={y(t) + 4} textAnchor="end">
              {fmt(t)}
            </text>
          </g>
        ))}
        <line
          className="chart-baseline"
          x1={pad.left}
          x2={W - pad.right}
          y1={H - pad.bottom}
          y2={H - pad.bottom}
        />
        {gens.map((g, i) =>
          i % labelEvery === 0 || i === values.length - 1 ? (
            <text key={g} className="chart-axis" x={x(i)} y={H - 10} textAnchor="middle">
              {g}
            </text>
          ) : null,
        )}
        <path className="chart-area" d={area} />
        <path className="chart-line" d={line} />
        {changes.map(({ v, i }) => (
          <g key={i}>
            <circle
              className={i === values.length - 1 ? "chart-dot last" : "chart-dot"}
              cx={x(i)}
              cy={y(v)}
              r={i === values.length - 1 ? 6 : 4}
            >
              <title>{`Thế hệ ${gens[i]}: điểm phạt ${v}`}</title>
            </circle>
            <text
              className="chart-label"
              x={x(i)}
              y={y(v) - 11}
              textAnchor={i === 0 ? "start" : i === values.length - 1 ? "end" : "middle"}
            >
              {fmt(v)}
            </text>
          </g>
        ))}
      </svg>
      <p className="chart-caption">
        Trục ngang là thế hệ, trục dọc là điểm phạt mềm tốt nhất (đã phóng theo khoảng giá
        trị để thấy rõ thay đổi). Giảm từ <strong>{first}</strong> xuống{" "}
        <strong>{last}</strong>
        {first > 0 ? ` (${Math.round(((first - last) / first) * 100)}%)` : ""}.
        {hardFirst !== undefined && hardFirst !== hardLast
          ? ` Vi phạm cứng: ${hardFirst} → ${hardLast}.`
          : ""}
      </p>
    </>
  );
}
 
function ConstraintGroup({ title, type, data, empty }) {
  const entries = Object.entries(data);
 
  return (
    <div className={`rule-group ${type}`}>
      <h4>
        {title}
        <span>{entries.length === 0 ? empty : `${entries.length} quy tắc`}</span>
      </h4>
      {entries.length > 0 && (
        <ul>
          {entries.map(([key, value]) => {
            const [name, hint] = CONSTRAINTS[key] || [key, ""];
            return (
              <li key={key}>
                <div>
                  <span className="rule-name">{name}</span>
                  {hint && <span className="rule-hint">{hint}</span>}
                </div>
                <strong>{value}</strong>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
 
function ComparisonTable({ comparison }) {
  const rows = comparison.rows;
  const best = {
    hard: Math.min(...rows.map((r) => r.fitness.hard_violations)),
    soft: Math.min(...rows.map((r) => r.fitness.soft_penalty)),
    reward: Math.max(...rows.map((r) => r.fitness.preference_reward)),
    time: Math.min(...rows.map((r) => r.runtime_ms)),
  };
  const maxTime = Math.max(...rows.map((r) => r.runtime_ms), 1);
 
  return (
    <div className="compare-wrap">
      <table className="compare-table">
        <caption>
          Bộ dữ liệu {datasetById[comparison.dataset].name.toLowerCase()}. Ô có dấu ✓ là kết
          quả tốt nhất ở mỗi cột.
        </caption>
        <thead>
          <tr>
            <th scope="col">Thuật toán</th>
            <th scope="col">Vi phạm cứng</th>
            <th scope="col">Điểm phạt mềm</th>
            <th scope="col">Điểm thưởng</th>
            <th scope="col">Thời gian</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.algorithm}>
              <th scope="row">{algorithmById[row.algorithm].name}</th>
              <td className={row.fitness.hard_violations === best.hard ? "best" : ""}>
                <span className={row.fitness.hard_violations === 0 ? "num ok" : "num bad"}>
                  {row.fitness.hard_violations}
                </span>
              </td>
              <td className={row.fitness.soft_penalty === best.soft ? "best" : ""}>
                {row.fitness.soft_penalty}
              </td>
              <td className={row.fitness.preference_reward === best.reward ? "best" : ""}>
                {row.fitness.preference_reward}
              </td>
              <td className={row.runtime_ms === best.time ? "best" : ""}>
                <div className="time-cell">
                  <span>{formatMs(row.runtime_ms)}</span>
                  <span className="time-bar" aria-hidden="true">
                    <span style={{ width: `${Math.max((row.runtime_ms / maxTime) * 100, 2)}%` }} />
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
 
function EmptyTimetable() {
  return (
    <div className="empty-timetable" aria-hidden="false">
      <div className="ghost-grid" aria-hidden="true">
        {Array.from({ length: 24 }, (_, i) => (
          <span key={i} className={[3, 8, 13, 18, 21].includes(i) ? "filled" : ""} />
        ))}
      </div>
      <p>
        Chưa có lịch để hiển thị. Tạo thời khóa biểu ở phần cấu hình, sau đó chọn
        lớp, giảng viên hoặc phòng để xem lịch tuần.
      </p>
      <a className="btn-ghost" href="#cau-hinh">
        Đến phần cấu hình
      </a>
    </div>
  );
}