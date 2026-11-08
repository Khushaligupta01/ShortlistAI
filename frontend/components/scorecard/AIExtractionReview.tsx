"use client";

import type { JDExtractionResult } from "@/lib/types";

interface AIExtractionReviewProps {
  data: JDExtractionResult;
  onApplyToScorecard?: () => void;
}

export default function AIExtractionReview({
  data,
  onApplyToScorecard,
}: AIExtractionReviewProps) {
  return (
    <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-6 shadow-xs space-y-6">
      {/* Header Banner */}
      <div className="flex items-start justify-between gap-4 border-b border-[#E8E2D8] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-[#EDE5D9] text-[#756653] text-xs font-bold border border-[#D9D1C5]">
              AI
            </span>
            <h3 className="font-semibold text-[#292722] text-base">
              AI Requirement Extraction Review
            </h3>
          </div>
          <p className="text-xs text-[#6F6A61] mt-1">
            Carefully review all extracted requirements. AI-extracted items must be verified by a recruiter before finalizing.
          </p>
        </div>
        {onApplyToScorecard && (
          <button
            type="button"
            onClick={onApplyToScorecard}
            className="text-xs font-semibold text-[#756653] bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#E8E2D8] px-3.5 py-1.5 rounded-xl transition-colors shrink-0 shadow-2xs"
          >
            Apply Extracted to Scorecard ↓
          </button>
        )}
      </div>

      {/* Warnings Banner if any */}
      {data.extraction_warnings && data.extraction_warnings.length > 0 && (
        <div className="bg-[#FDF6E7] border border-[#F1DCAC] rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 text-[#7A5212] text-xs font-semibold">
            <svg className="w-4 h-4 text-[#7A5212] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Extraction Warnings ({data.extraction_warnings.length})
          </div>
          <ul className="text-xs text-[#7A5212] space-y-1 pl-6 list-disc">
            {data.extraction_warnings.map((w, idx) => (
              <li key={idx}>
                <span className="font-medium capitalize">{w.field}:</span> {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Structured Fields Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Experience */}
        <div className="bg-[#F5F1EA] rounded-xl p-4 border border-[#E8E2D8]">
          <p className="text-xs font-semibold text-[#6F6A61] uppercase tracking-wider">Experience</p>
          {data.experience ? (
            <div className="mt-2">
              <p className="text-base font-bold text-[#292722]">
                {data.experience.minimum_years ?? 0}
                {data.experience.maximum_years ? ` - ${data.experience.maximum_years}` : "+"} Years
              </p>
              {data.experience.evidence && (
                <p className="text-xs text-[#6F6A61] italic mt-1.5 bg-[#FFFFFF] p-2.5 rounded-lg border border-[#E8E2D8]">
                  &ldquo;{data.experience.evidence}&rdquo;
                </p>
              )}
              <span className={`inline-block mt-2 text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                data.experience.is_explicit ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]" : "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
              }`}>
                {data.experience.is_explicit ? "Explicit in JD" : "Inferred"}
              </span>
            </div>
          ) : (
            <p className="text-xs text-[#918A80] italic mt-2">Not specified in JD</p>
          )}
        </div>

        {/* Notice Period */}
        <div className="bg-[#F5F1EA] rounded-xl p-4 border border-[#E8E2D8]">
          <p className="text-xs font-semibold text-[#6F6A61] uppercase tracking-wider">Notice Period</p>
          {data.notice_period?.maximum_days != null ? (
            <div className="mt-2">
              <p className="text-base font-bold text-[#292722]">
                Max {data.notice_period.maximum_days} Days
              </p>
              {data.notice_period.original_wording && (
                <p className="text-xs text-[#6F6A61] italic mt-1.5 bg-[#FFFFFF] p-2.5 rounded-lg border border-[#E8E2D8]">
                  &ldquo;{data.notice_period.original_wording}&rdquo;
                </p>
              )}
              <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-full font-semibold bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC]">
                Explicit in JD
              </span>
            </div>
          ) : (
            <p className="text-xs text-[#918A80] italic mt-2">Not specified in JD (remains null)</p>
          )}
        </div>

        {/* Location & Details */}
        <div className="bg-[#F5F1EA] rounded-xl p-4 border border-[#E8E2D8]">
          <p className="text-xs font-semibold text-[#6F6A61] uppercase tracking-wider">Location & Terms</p>
          <div className="mt-2 space-y-1.5 text-xs">
            <p className="text-[#292722]">
              <span className="font-medium text-[#6F6A61]">Location:</span> {data.location || "Not specified"}
            </p>
            {data.work_arrangement && (
              <p className="text-[#292722]">
                <span className="font-medium text-[#6F6A61]">Arrangement:</span> {data.work_arrangement}
              </p>
            )}
            {data.employment_type && (
              <p className="text-[#292722]">
                <span className="font-medium text-[#6F6A61]">Type:</span> {data.employment_type}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Must-Have Skills */}
      <div>
        <p className="text-xs font-bold text-[#292722] uppercase tracking-wider mb-2">
          Must-Have Skills ({data.must_have_skills.length})
        </p>
        {data.must_have_skills.length === 0 ? (
          <p className="text-xs text-[#918A80] italic">No mandatory skills extracted.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.must_have_skills.map((skill, i) => (
              <div
                key={i}
                className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#292722] text-xs">{skill.name}</span>
                  <span className="text-[10px] font-semibold bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-md border border-[#D9D1C5]">
                    Mandatory
                  </span>
                </div>
                {skill.evidence && (
                  <p className="text-[11px] text-[#6F6A61] italic mt-1.5 line-clamp-2">
                    &ldquo;{skill.evidence}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Nice-To-Have Skills */}
      {data.nice_to_have_skills.length > 0 && (
        <div>
          <p className="text-xs font-bold text-[#292722] uppercase tracking-wider mb-2">
            Preferred / Nice-to-Have Skills ({data.nice_to_have_skills.length})
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.nice_to_have_skills.map((skill, i) => (
              <div
                key={i}
                className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[#292722] text-xs">{skill.name}</span>
                  <span className="text-[10px] bg-[#FFFFFF] border border-[#E8E2D8] text-[#6F6A61] px-2 py-0.5 rounded-md">
                    Preferred
                  </span>
                </div>
                {skill.evidence && (
                  <p className="text-[11px] text-[#6F6A61] italic mt-1.5 line-clamp-2">
                    &ldquo;{skill.evidence}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Additional Requirements */}
      {data.additional_requirements && data.additional_requirements.length > 0 && (
        <div>
          <p className="text-xs font-bold text-[#292722] uppercase tracking-wider mb-2">
            Additional Requirements ({data.additional_requirements.length})
          </p>
          <div className="space-y-2">
            {data.additional_requirements.map((req, i) => (
              <div key={i} className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase font-bold text-[#6F6A61] bg-[#FFFFFF] border border-[#E8E2D8] px-1.5 py-0.5 rounded">
                    {req.category}
                  </span>
                  <span className="font-medium text-[#292722]">{req.description}</span>
                  {req.is_mandatory && (
                    <span className="text-[10px] text-[#7A5212] bg-[#FDF6E7] border border-[#F1DCAC] px-1.5 py-0.5 rounded font-semibold ml-auto">
                      Required
                    </span>
                  )}
                </div>
                {req.evidence && (
                  <p className="text-[11px] text-[#6F6A61] italic mt-1">
                    &ldquo;{req.evidence}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
