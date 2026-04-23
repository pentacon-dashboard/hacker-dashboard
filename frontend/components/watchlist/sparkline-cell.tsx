"use client";

interface SparklineCellProps {
  data: number[];
  width?: number;
  height?: number;
}

export function SparklineCell({ data, width = 50, height = 20 }: SparklineCellProps) {
  if (!data || data.length < 2) {
    return (
      <span
        className="inline-block text-muted-foreground"
        style={{ width, height }}
        aria-label="스파크라인 데이터 없음"
      >
        —
      </span>
    );
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const polyline = points.join(" ");
  const isPositive = data[data.length - 1]! >= data[0]!;
  const stroke = isPositive ? "#10b981" : "#ef4444";

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-label="7일 스파크라인"
      className="inline-block"
    >
      <polyline
        points={polyline}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
