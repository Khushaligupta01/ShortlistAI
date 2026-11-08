"use client";

import React from "react";
import { X, Award, ShieldAlert, CheckCircle, Calculator, Info } from "lucide-react";

interface ScoringExplanationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ScoringExplanationModal({
  isOpen,
  onClose,
}: ScoringExplanationModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#292722]/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-[#FFFFFF] rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden border border-[#E8E2D8] flex flex-col text-[#292722]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] shrink-0">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-[#756653]" />
            <div>
              <h3 className="text-sm font-serif font-bold text-[#292722]">
                Deterministic Scoring & Evaluation Methodology
              </h3>
              <p className="text-[11px] text-[#6F6A61]">
                Transparent mathematical scoring without black-box AI bias
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#918A80] hover:text-[#292722] rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto text-xs text-[#6F6A61] leading-relaxed">
          {/* Key Principle 1: No LLM Score Assignment */}
          <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-4 space-y-2">
            <h4 className="font-serif font-bold text-[#292722] flex items-center gap-2 text-xs">
              <CheckCircle className="w-4 h-4 text-[#756653] shrink-0" />
              1. The AI Never Assigns Scores
            </h4>
            <p className="text-[#292722] text-xs">
              Large Language Models are strictly used as evidence extraction assistants to locate verbatim text in resumes corresponding to approved job scorecard criteria. All numerical points are computed by deterministic Python algorithms in accordance with the scorecard weights.
            </p>
          </div>

          {/* Standard Category Weights Table */}
          <div className="space-y-2">
            <h4 className="font-serif font-bold text-[#292722] text-xs flex items-center gap-2">
              <Award className="w-4 h-4 text-[#756653] shrink-0" />
              2. Scorecard Weights & Point Distribution (100 Points Total)
            </h4>
            <div className="border border-[#E8E2D8] rounded-xl overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead className="bg-[#F5F1EA] text-[11px] font-semibold text-[#6F6A61] border-b border-[#E8E2D8]">
                  <tr>
                    <th className="py-2 px-3">Evaluation Category</th>
                    <th className="py-2 px-3">Weight</th>
                    <th className="py-2 px-3">Scoring Logic</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFEAE2] text-[11px]">
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#292722]">Must-Have Skills</td>
                    <td className="py-2 px-3 font-mono font-bold text-[#756653]">40 pts</td>
                    <td className="py-2 px-3 text-[#6F6A61]">Full points for MATCHED, 50% for PARTIAL. Missing evidence receives 0 pts.</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#292722]">Experience Years</td>
                    <td className="py-2 px-3 font-mono font-bold text-[#756653]">30 pts</td>
                    <td className="py-2 px-3 text-[#6F6A61]">Within range = 100%. Above maximum = 100% (never penalized). Below min = proportional.</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#292722]">Notice Period</td>
                    <td className="py-2 px-3 font-mono font-bold text-[#756653]">15 pts</td>
                    <td className="py-2 px-3 text-[#6F6A61]">Within max notice days = 100%. Missing/unknown = provisional exclusion (not penalized).</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#292722]">Location Compatibility</td>
                    <td className="py-2 px-3 font-mono font-bold text-[#756653]">10 pts</td>
                    <td className="py-2 px-3 text-[#6F6A61]">Matching city or Remote = 100%. Missing/unknown = provisional exclusion (not penalized).</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-semibold text-[#292722]">Nice-to-Have Skills</td>
                    <td className="py-2 px-3 font-mono font-bold text-[#756653]">5 pts</td>
                    <td className="py-2 px-3 text-[#6F6A61]">Bonus points awarded for relevant additional skills found on resume.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Provisional Normalization & Missing Information */}
          <div className="space-y-2">
            <h4 className="font-serif font-bold text-[#292722] text-xs flex items-center gap-2">
              <Info className="w-4 h-4 text-[#756653] shrink-0" />
              3. Fair Treatment of Missing Information (Provisional Normalization)
            </h4>
            <p className="text-[#6F6A61]">
              Resumes frequently omit logistical details such as notice period or location. In ShortlistAI, missing information is marked as <code className="bg-[#F5F1EA] text-[#292722] px-1 py-0.5 rounded font-mono border border-[#E8E2D8]">UNKNOWN</code> and is <strong>never silently penalized as a zero</strong>. Instead, the candidate receives a <em>Provisional Normalized Score</em> calculated against the verifiable criteria, paired with an Evidence Coverage indicator.
            </p>
          </div>

          {/* Responsible AI & Anti-Rejection Policy */}
          <div className="bg-[#EEF6F0] border border-[#C4E2CC] rounded-xl p-4 space-y-2">
            <h4 className="font-serif font-bold text-[#2A5A35] flex items-center gap-2 text-xs">
              <ShieldAlert className="w-4 h-4 text-[#2A5A35] shrink-0" />
              4. Zero Automatic Rejection Policy
            </h4>
            <p className="text-[#2A5A35] text-xs">
              ShortlistAI has zero automatic rejection thresholds. Low-scoring candidates remain permanently visible and searchable on the requisition. Only authorized human recruiters have the authority to make shortlisting, rejection, or hold decisions.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#F5F1EA] border-t border-[#E8E2D8] flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="bg-[#756653] hover:bg-[#5F5243] text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
