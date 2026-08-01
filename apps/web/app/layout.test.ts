import { metadata } from "@/app/layout";
import { describe, expect, it } from "vitest";

describe("page metadata", () => {
  it("describes scheduled destinations without claiming current availability", () => {
    expect(metadata.description).toContain("scheduled");
    expect(metadata.description).not.toContain("fly today");
  });
});
