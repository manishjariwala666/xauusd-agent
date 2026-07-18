import assert from "node:assert/strict";
import test from "node:test";

import { proxyAutomationEnquiry } from "../lib/automation-enquiry-proxy.ts";

const request = {
  backendBaseUrl: "https://api.example.test",
  body: JSON.stringify({ name: "Test User" }),
  forwardedFor: "127.0.0.1",
};

test("preserves a backend 201 JSON response", async () => {
  let calls = 0;
  const result = await proxyAutomationEnquiry({
    ...request,
    fetchImplementation: async () => {
      calls += 1;
      return Response.json(
        { message: "Enquiry received.", reference: "VR-TEST" },
        { status: 201 },
      );
    },
  });

  assert.equal(calls, 1);
  assert.equal(result.status, 201);
  assert.deepEqual(result.payload, {
    message: "Enquiry received.",
    reference: "VR-TEST",
  });
});

test("preserves a backend 4xx JSON response", async () => {
  const result = await proxyAutomationEnquiry({
    ...request,
    fetchImplementation: async () =>
      Response.json({ detail: "Validation failed." }, { status: 422 }),
  });

  assert.equal(result.status, 422);
  assert.deepEqual(result.payload, { detail: "Validation failed." });
});

test("converts a malformed successful response to a safe 502", async () => {
  const result = await proxyAutomationEnquiry({
    ...request,
    fetchImplementation: async () =>
      new Response("not-json", {
        status: 201,
        headers: { "Content-Type": "text/plain" },
      }),
  });

  assert.equal(result.status, 502);
  assert.deepEqual(result.payload, {
    message: "Enquiry service returned an invalid response.",
  });
});

test("returns a safe 503 when the backend request fails", async () => {
  const result = await proxyAutomationEnquiry({
    ...request,
    fetchImplementation: async () => {
      throw new TypeError("network unavailable");
    },
  });

  assert.equal(result.status, 503);
  assert.deepEqual(result.payload, {
    message: "Enquiry service is temporarily unavailable.",
  });
});
