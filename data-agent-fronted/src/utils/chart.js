export function detectNumeric(columns, rows) {
  const map = {};
  for (const col of columns) {
    map[col] = rows.every((row) => {
      const value = row[col];
      return value == null || value === "" || Number.isFinite(Number(value));
    });
  }
  return map;
}

export function inferChartType(columns, rows, numeric) {
  const cats = columns.filter((c) => !numeric[c]);
  const nums = columns.filter((c) => numeric[c]);
  if (!rows.length || cats.length !== 1 || nums.length < 1) return "table";
  const catCol = cats[0];
  if (/date|年|月|日|week|时间|date_id/i.test(catCol)) return "line";
  return "bar";
}

export function formatNumber(value) {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  return Number.isInteger(num)
    ? String(num)
    : num.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

export function buildConclusion(columns, rows, numeric) {
  if (!rows.length) return "没有查到数据。";
  const nums = columns.filter((c) => numeric[c]);
  const cats = columns.filter((c) => !numeric[c]);
  if (cats.length === 1 && nums.length >= 1) {
    const numCol = nums[0];
    const catCol = cats[0];
    const sorted = [...rows].sort((a, b) => Number(b[numCol]) - Number(a[numCol]));
    const top = sorted[0];
    return `${catCol}中「${top[catCol]}」的${numCol}最高，为 ${formatNumber(top[numCol])}。共 ${rows.length} 行。`;
  }
  return `查询返回 ${rows.length} 行、${columns.length} 列。`;
}

export function buildChartOption(type, columns, rows, numeric) {
  const cats = columns.filter((c) => !numeric[c]);
  const nums = columns.filter((c) => numeric[c]);
  if (type === "table" || !cats.length || !nums.length) return null;
  const catCol = cats[0];
  const categories = rows.map((row) => String(row[catCol] ?? ""));
  const series = nums.map((col) => ({
    name: col,
    type: type === "pie" ? "pie" : type,
    data:
      type === "pie"
        ? rows.map((row) => ({ name: String(row[catCol] ?? ""), value: Number(row[col]) || 0 }))
        : rows.map((row) => Number(row[col]) || 0),
    radius: type === "pie" ? "65%" : undefined,
  }));
  if (type === "pie") {
    return {
      tooltip: { trigger: "item" },
      series,
    };
  }
  return {
    tooltip: { trigger: "axis" },
    legend: nums.length > 1 ? { top: 0 } : undefined,
    grid: { left: 48, right: 16, top: 36, bottom: 32 },
    xAxis: { type: "category", data: categories, axisLabel: { interval: 0 } },
    yAxis: { type: "value" },
    series,
  };
}
