import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LogoBadge } from "./logo-badge";

describe("LogoBadge", () => {
  it("펼침 상태에서 HACKER + DASHBOARD 텍스트를 렌더한다", () => {
    render(<LogoBadge collapsed={false} />);
    expect(screen.getByText("HACKER")).toBeInTheDocument();
    expect(screen.getByText("DASHBOARD")).toBeInTheDocument();
  });

  it("접힘 상태에서 HD 약식 텍스트를 렌더한다", () => {
    render(<LogoBadge collapsed={true} />);
    expect(screen.getByText("HD")).toBeInTheDocument();
  });

  it("접힘 상태에서 HACKER 텍스트가 없어야 한다", () => {
    render(<LogoBadge collapsed={true} />);
    expect(screen.queryByText("HACKER")).not.toBeInTheDocument();
  });
});
