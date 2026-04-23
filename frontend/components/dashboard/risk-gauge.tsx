"use client";

interface RiskGaugeProps {
  /** 0~100 범위의 리스크 점수 */
  score: number;
  /** 중앙 표시 라벨 (기본: "{score}%") */
  valueLabel?: string;
  /** 하단 부제 */
  caption?: string;
}

function riskColor(score: number): string {
  if (score >= 66) return "#ef4444"; // red-500
  if (score >= 33) return "#f59e0b"; // amber-500
  return "#10b981"; // emerald-500
}

function riskBand(score: number): string {
  if (score >= 66) return "높음";
  if (score >= 33) return "보통";
  return "양호";
}

export function RiskGauge({ score, valueLabel, caption }: RiskGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const stroke = riskColor(clamped);

  // 반원 게이지: 180도 호. SVG path arc 계산.
  const size = 200;
  const center = size / 2;
  const radius = 80;
  const strokeWidth = 16;

  // 반원 전체 둘레 = π * r
  const semiCircumference = Math.PI * radius;
  const dashArray = semiCircumference;
  const dashOffset = semiCircumference * (1 - clamped / 100);

  return (
    <div
      className="flex flex-col items-center justify-center"
      role="img"
      aria-label={`리스크 점수 ${clamped.toFixed(1)}%, ${riskBand(clamped)}`}
      data-testid="risk-gauge"
    >
      <svg
        width={size}
        height={size / 2 + strokeWidth}
        viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}
        aria-hidden="true"
      >
        {/* 배경 arc */}
        <path
          d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
          fill="none"
          className="stroke-muted"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* 값 arc */}
        <path
          d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
          fill="none"
          stroke={stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={dashArray}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 600ms ease-out" }}
        />
      </svg>
      <div className="-mt-16 text-center">
        <div className="text-3xl font-bold tabular-nums" style={{ color: stroke }}>
          {valueLabel ?? `${clamped.toFixed(1)}%`}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {caption ?? `집중도 ${riskBand(clamped)}`}
        </div>
      </div>
    </div>
  );
}
