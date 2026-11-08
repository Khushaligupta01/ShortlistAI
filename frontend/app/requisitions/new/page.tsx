"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import AIExtractionReview from "@/components/scorecard/AIExtractionReview";
import ScorecardEditor, {
  ScorecardEditorState,
} from "@/components/scorecard/ScorecardEditor";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type {
  CurrentUser,
  JDExtractionResult,
  ScorecardCriterion,
} from "@/lib/types";

export default function NewRequisitionPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);

  // Form Fields
  const [title, setTitle] = useState("Senior Java Developer");
  const [location, setLocation] = useState("Noida");
  const [jobDescription, setJobDescription] = useState(
    "We are looking for a Senior Java Developer to join our backend engineering team in Noida.\n\n" +
      "Responsibilities:\n" +
      "- Design, develop, and maintain high-performance enterprise applications.\n" +
      "- Develop robust REST APIs and backend microservices.\n" +
      "- Collaborate with engineering and product teams.\n\n" +
      "Requirements:\n" +
      "- 5-8 years of professional software development experience.\n" +
      "- Strong Java development experience required.\n" +
      "- Hands-on Spring Boot experience required.\n" +
      "- Location: Noida.\n" +
      "- Notice period: Notice period up to 60 days.\n\n" +
      "Preferred Qualifications:\n" +
      "- Microservices experience preferred."
  );

  // Extraction State
  const [extracting, setExtracting] = useState(false);
  const [extractionResult, setExtractionResult] =
    useState<JDExtractionResult | null>(null);
  const [extractionError, setExtractionError] = useState<string | null>(null);

  // Scorecard Editor State
  const [scorecardState, setScorecardState] = useState<
    Partial<ScorecardEditorState>
  >({
    experience_min: 5,
    experience_max: 8,
    location: "Noida",
    max_notice_days: 60,
    scoring_config: {
      experience: 30,
      must_have_skills: 40,
      notice_period: 15,
      location: 10,
      nice_to_have_skills: 5,
    },
    criteria: [
      {
        criterion_type: "must_have_skill",
        criterion_name: "Java",
        normalized_name: "java",
        label: "Java",
        description: "Core Java enterprise development",
        weight: 20,
        is_mandatory: true,
        evidence_from_jd: "Strong Java development experience required",
        display_order: 0,
      },
      {
        criterion_type: "must_have_skill",
        criterion_name: "Spring Boot",
        normalized_name: "spring_boot",
        label: "Spring Boot",
        description: "Hands-on Spring Boot framework",
        weight: 20,
        is_mandatory: true,
        evidence_from_jd: "Hands-on Spring Boot experience required",
        display_order: 1,
      },
      {
        criterion_type: "nice_to_have_skill",
        criterion_name: "Microservices",
        normalized_name: "microservices",
        label: "Microservices",
        description: "Microservices architecture",
        weight: 5,
        is_mandatory: false,
        evidence_from_jd: "Microservices experience preferred",
        display_order: 2,
      },
    ],
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api
      .getCurrentUser()
      .then((u) => {
        if (u.role !== "recruiter") {
          router.replace("/dashboard");
          return;
        }
        setUser(u);
      })
      .catch((err) => setError(err.message));
  }, [router]);

  // Handle AI Extraction trigger
  async function handleExtractRequirements() {
    if (!jobDescription.trim() || jobDescription.trim().length < 10) {
      setExtractionError("Please provide a job description with at least 10 characters.");
      return;
    }

    setExtracting(true);
    setExtractionError(null);
    try {
      const result = await api.extractRequirements(jobDescription.trim());
      setExtractionResult(result);

      // Pre-populate scorecard from AI extraction
      applyExtractionToScorecard(result);
    } catch (err: unknown) {
      setExtractionError(
        err instanceof Error
          ? err.message
          : "AI extraction failed. You can still manually configure criteria below."
      );
    } finally {
      setExtracting(false);
    }
  }

  // Map extraction result to scorecard state
  function applyExtractionToScorecard(ext: JDExtractionResult) {
    if (ext.job_title && !title) setTitle(ext.job_title);
    if (ext.location) setLocation(ext.location);

    const newCriteria: ScorecardCriterion[] = [];

    // Must-have skills
    ext.must_have_skills.forEach((skill, idx) => {
      newCriteria.push({
        criterion_type: "must_have_skill",
        criterion_name: skill.name,
        normalized_name: skill.normalized_name,
        label: skill.name,
        description: skill.description || `${skill.name} proficiency`,
        weight: Math.round(40 / Math.max(1, ext.must_have_skills.length)),
        is_mandatory: true,
        evidence_from_jd: skill.evidence,
        display_order: idx,
      });
    });

    // Nice-to-have skills
    ext.nice_to_have_skills.forEach((skill, idx) => {
      newCriteria.push({
        criterion_type: "nice_to_have_skill",
        criterion_name: skill.name,
        normalized_name: skill.normalized_name,
        label: skill.name,
        description: skill.description || `${skill.name} preferred`,
        weight: Math.round(5 / Math.max(1, ext.nice_to_have_skills.length)),
        is_mandatory: false,
        evidence_from_jd: skill.evidence,
        display_order: newCriteria.length + idx,
      });
    });

    setScorecardState({
      experience_min: ext.experience?.minimum_years ?? "",
      experience_max: ext.experience?.maximum_years ?? "",
      location: ext.location ?? location,
      max_notice_days: ext.notice_period?.maximum_days ?? "",
      scoring_config: {
        experience: 30,
        must_have_skills: 40,
        notice_period: 15,
        location: 10,
        nice_to_have_skills: 5,
      },
      criteria: newCriteria,
    });
  }

  // Save as Draft
  async function handleSaveDraft(scState: ScorecardEditorState) {
    setError(null);
    setSaving(true);
    try {
      // 1. Create Requisition
      const req = await api.createRequisition({
        title: title.trim(),
        location: location.trim() || undefined,
        job_description: jobDescription.trim(),
      });

      // 2. Create Draft Scorecard
      await api.createScorecard(req.id, {
        experience_min:
          scState.experience_min === "" ? null : Number(scState.experience_min),
        experience_max:
          scState.experience_max === "" ? null : Number(scState.experience_max),
        location: scState.location || undefined,
        max_notice_days:
          scState.max_notice_days === "" ? null : Number(scState.max_notice_days),
        scoring_config: scState.scoring_config,
        criteria: scState.criteria,
        jd_extraction_json: (extractionResult as unknown as Record<string, unknown>) || undefined,
      });

      router.push(`/requisitions/${req.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create requisition");
    } finally {
      setSaving(false);
    }
  }

  // Save and Approve
  async function handleApprove(scState: ScorecardEditorState) {
    setError(null);
    setSaving(true);
    try {
      // 1. Create Requisition
      const req = await api.createRequisition({
        title: title.trim(),
        location: location.trim() || undefined,
        job_description: jobDescription.trim(),
      });

      // 2. Create Draft Scorecard
      await api.createScorecard(req.id, {
        experience_min:
          scState.experience_min === "" ? null : Number(scState.experience_min),
        experience_max:
          scState.experience_max === "" ? null : Number(scState.experience_max),
        location: scState.location || undefined,
        max_notice_days:
          scState.max_notice_days === "" ? null : Number(scState.max_notice_days),
        scoring_config: scState.scoring_config,
        criteria: scState.criteria,
        jd_extraction_json: (extractionResult as unknown as Record<string, unknown>) || undefined,
      });

      // 3. Approve and activate
      await api.approveScorecard(req.id);

      router.push(`/requisitions/${req.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to approve requisition");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Breadcrumb & Title */}
        <div className="pb-2 border-b border-[#E8E2D8]">
          <Link
            href="/requisitions"
            className="text-xs font-semibold text-[#6F6A61] hover:text-[#756653] inline-flex items-center gap-1 mb-2"
          >
            ← Back to Requisitions
          </Link>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-[#292722] tracking-tight">
              Create New Requisition & Scorecard
            </h1>
            <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
              Setup Wizard
            </span>
          </div>
          <p className="text-xs text-[#6F6A61] mt-1">
            Input the job details, extract structured requirements using AI, and configure the dynamic evaluation scorecard.
          </p>
        </div>

        {error && (
          <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] text-xs font-medium p-4 rounded-xl">
            {error}
          </div>
        )}

        {/* Section A: Job Description Input */}
        <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-6 shadow-xs space-y-4">
          <h2 className="font-semibold text-[#292722] text-base border-b border-[#E8E2D8] pb-2">
            Step 1: Job Description
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                Job Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Senior Java Developer"
                className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none font-medium"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Noida / Hybrid"
                className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-[#6F6A61]">
                Job Description Text *
              </label>
              <span className="text-[11px] text-[#918A80]">
                {jobDescription.length} characters
              </span>
            </div>
            <textarea
              rows={8}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste or type the comprehensive job description here..."
              className="w-full text-xs font-mono border border-[#E8E2D8] rounded-xl p-3 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none leading-relaxed"
              required
            />
          </div>

          {/* AI Trigger Action */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-[#E8E2D8]">
            <p className="text-xs text-[#6F6A61]">
              Trigger AI extraction to automatically extract experience, skills, location, and notice period.
            </p>
            <button
              type="button"
              disabled={extracting}
              onClick={handleExtractRequirements}
              className="inline-flex items-center justify-center gap-2 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-2xs disabled:opacity-50"
            >
              {extracting ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-[#FAF9F6] border-t-transparent rounded-full animate-spin" />
                  Extracting Requirements...
                </>
              ) : (
                <>
                  <span>✨</span>
                  Extract Requirements with AI
                </>
              )}
            </button>
          </div>

          {/* Extraction Error Notice */}
          {extractionError && (
            <div className="bg-[#FDF6E7] border border-[#F1DCAC] text-[#7A5212] text-xs p-3 rounded-xl flex items-start gap-2">
              <span className="font-bold text-[#7A5212]">Notice:</span>
              <div>
                <p>{extractionError}</p>
                <p className="text-[11px] text-[#7A5212] mt-1">
                  You can proceed by entering and editing scorecard criteria manually below.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Section B: AI Extraction Review (if extracted) */}
        {extractionResult && (
          <AIExtractionReview
            data={extractionResult}
            onApplyToScorecard={() => applyExtractionToScorecard(extractionResult)}
          />
        )}

        {/* Section C: Scorecard Editor */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-[#292722] text-base">
              Step 2: Scorecard & Dynamic Criteria
            </h2>
            <span className="text-xs text-[#6F6A61]">
              Configure weights, add/remove requirements, and publish.
            </span>
          </div>

          <ScorecardEditor
            initialState={scorecardState}
            onSaveDraft={handleSaveDraft}
            onApprove={handleApprove}
            isLoading={saving}
          />
        </div>
      </main>
    </div>
  );
}
