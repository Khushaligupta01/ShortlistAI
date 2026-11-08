"use client";

import { useEffect, useState } from "react";
import type { ScorecardCriterion, ScoringConfig } from "@/lib/types";

export interface ScorecardEditorState {
  experience_min: number | "";
  experience_max: number | "";
  location: string;
  max_notice_days: number | "";
  scoring_config: ScoringConfig;
  criteria: ScorecardCriterion[];
}

interface ScorecardEditorProps {
  initialState?: Partial<ScorecardEditorState>;
  isLocked?: boolean;
  versionNumber?: number;
  onSaveDraft?: (state: ScorecardEditorState) => Promise<void>;
  onApprove?: (state: ScorecardEditorState) => Promise<void>;
  isLoading?: boolean;
}

const DEFAULT_CONFIG: ScoringConfig = {
  experience: 30,
  must_have_skills: 40,
  notice_period: 15,
  location: 10,
  nice_to_have_skills: 5,
};

export default function ScorecardEditor({
  initialState,
  isLocked = false,
  versionNumber = 1,
  onSaveDraft,
  onApprove,
  isLoading = false,
}: ScorecardEditorProps) {
  const [experienceMin, setExperienceMin] = useState<number | "">(
    initialState?.experience_min ?? ""
  );
  const [experienceMax, setExperienceMax] = useState<number | "">(
    initialState?.experience_max ?? ""
  );
  const [location, setLocation] = useState<string>(initialState?.location ?? "");
  const [maxNoticeDays, setMaxNoticeDays] = useState<number | "">(
    initialState?.max_notice_days ?? ""
  );
  const [scoringConfig, setScoringConfig] = useState<ScoringConfig>(
    initialState?.scoring_config ?? DEFAULT_CONFIG
  );
  const [criteria, setCriteria] = useState<ScorecardCriterion[]>(
    initialState?.criteria ?? []
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Sync state if initialState changes
  useEffect(() => {
    if (initialState) {
      if (initialState.experience_min !== undefined)
        setExperienceMin(initialState.experience_min ?? "");
      if (initialState.experience_max !== undefined)
        setExperienceMax(initialState.experience_max ?? "");
      if (initialState.location !== undefined)
        setLocation(initialState.location ?? "");
      if (initialState.max_notice_days !== undefined)
        setMaxNoticeDays(initialState.max_notice_days ?? "");
      if (initialState.scoring_config)
        setScoringConfig(initialState.scoring_config);
      if (initialState.criteria)
        setCriteria(initialState.criteria);
    }
  }, [initialState]);

  // Compute live scoring config total
  const configTotal =
    (Number(scoringConfig.experience) || 0) +
    (Number(scoringConfig.must_have_skills) || 0) +
    (Number(scoringConfig.notice_period) || 0) +
    (Number(scoringConfig.location) || 0) +
    (Number(scoringConfig.nice_to_have_skills) || 0);

  const isConfigValid = configTotal === 100;

  function updateConfig(field: keyof ScoringConfig, value: number) {
    if (isLocked) return;
    setScoringConfig((prev) => ({
      ...prev,
      [field]: Math.max(0, Math.min(100, value)),
    }));
  }

  function addCriterion() {
    if (isLocked) return;
    const newCrit: ScorecardCriterion = {
      criterion_type: "must_have_skill",
      criterion_name: "",
      normalized_name: "",
      label: "",
      description: "",
      weight: 10,
      is_mandatory: true,
      evidence_from_jd: "",
      display_order: criteria.length,
    };
    setCriteria([...criteria, newCrit]);
  }

  function updateCriterion(
    index: number,
    patch: Partial<ScorecardCriterion>
  ) {
    if (isLocked) return;
    setCriteria((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...patch };
      if (patch.label && !copy[index].criterion_name) {
        copy[index].criterion_name = patch.label;
      }
      if (patch.criterion_name && !copy[index].label) {
        copy[index].label = patch.criterion_name;
      }
      return copy;
    });
  }

  function removeCriterion(index: number) {
    if (isLocked) return;
    setCriteria((prev) => prev.filter((_, i) => i !== index));
  }

  function moveCriterion(index: number, direction: "up" | "down") {
    if (isLocked) return;
    if (direction === "up" && index === 0) return;
    if (direction === "down" && index === criteria.length - 1) return;
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    setCriteria((prev) => {
      const copy = [...prev];
      const temp = copy[index];
      copy[index] = copy[targetIdx];
      copy[targetIdx] = temp;
      return copy.map((c, i) => ({ ...c, display_order: i }));
    });
  }

  function getCurrentState(): ScorecardEditorState {
    return {
      experience_min: experienceMin === "" ? "" : Number(experienceMin),
      experience_max: experienceMax === "" ? "" : Number(experienceMax),
      location: location.trim(),
      max_notice_days: maxNoticeDays === "" ? "" : Number(maxNoticeDays),
      scoring_config: scoringConfig,
      criteria: criteria.map((c, idx) => ({
        ...c,
        criterion_name: c.criterion_name || c.label,
        label: c.label || c.criterion_name,
        normalized_name: (c.criterion_name || c.label)
          .toLowerCase()
          .trim()
          .replace(/\s+/g, "_"),
        display_order: idx,
      })),
    };
  }

  async function handleSaveDraft() {
    setError(null);
    setSuccessMessage(null);
    setSaving(true);
    try {
      const state = getCurrentState();
      if (onSaveDraft) await onSaveDraft(state);
      setSuccessMessage("Scorecard draft saved successfully.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save draft");
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove() {
    setError(null);
    setSuccessMessage(null);
    if (!isConfigValid) {
      setError(`Scoring configuration weights must sum to exactly 100 points (current: ${configTotal}).`);
      return;
    }
    if (criteria.length === 0) {
      setError("Scorecard must have at least one criterion before approval.");
      return;
    }
    // Check that every criterion has a name
    for (let i = 0; i < criteria.length; i++) {
      if (!criteria[i].criterion_name?.trim() && !criteria[i].label?.trim()) {
        setError(`Criterion #${i + 1} is missing a name.`);
        return;
      }
    }

    setSaving(true);
    try {
      const state = getCurrentState();
      if (onApprove) await onApprove(state);
      setSuccessMessage("Scorecard approved and published successfully!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Locked Alert if approved */}
      {isLocked && (
        <div className="bg-slate-100 border border-slate-300 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <div>
              <p className="text-xs font-semibold text-slate-800">
                Scorecard Version {versionNumber} is Approved and Locked
              </p>
              <p className="text-xs text-slate-500">
                Structural modifications are locked to preserve evaluation consistency. To edit, create a new version.
              </p>
            </div>
          </div>
          <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2.5 py-1 rounded-full">
            Approved
          </span>
        </div>
      )}

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-xs font-medium p-3 rounded-lg">
          {error}
        </div>
      )}
      {successMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium p-3 rounded-lg">
          {successMessage}
        </div>
      )}

      {/* Basic Requisition Specs */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <h4 className="font-semibold text-slate-800 text-sm mb-3">
          1. Role Requirements & Boundaries
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Minimum Experience (Yrs)
            </label>
            <input
              type="number"
              min="0"
              max="50"
              disabled={isLocked}
              value={experienceMin}
              onChange={(e) =>
                setExperienceMin(e.target.value === "" ? "" : Number(e.target.value))
              }
              placeholder="e.g. 5"
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 disabled:bg-slate-50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Maximum Experience (Yrs)
            </label>
            <input
              type="number"
              min="0"
              max="60"
              disabled={isLocked}
              value={experienceMax}
              onChange={(e) =>
                setExperienceMax(e.target.value === "" ? "" : Number(e.target.value))
              }
              placeholder="e.g. 8"
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 disabled:bg-slate-50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Target Location
            </label>
            <input
              type="text"
              disabled={isLocked}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Noida / Remote"
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 disabled:bg-slate-50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Max Notice Period (Days)
            </label>
            <input
              type="number"
              min="0"
              max="365"
              disabled={isLocked}
              value={maxNoticeDays}
              onChange={(e) =>
                setMaxNoticeDays(e.target.value === "" ? "" : Number(e.target.value))
              }
              placeholder="e.g. 60 (blank if unknown)"
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 disabled:bg-slate-50"
            />
          </div>
        </div>
      </div>

      {/* Scoring Weight Configuration */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h4 className="font-semibold text-slate-800 text-sm">
              2. Scoring Weights Configuration
            </h4>
            <p className="text-xs text-slate-500">
              Deterministic scoring model. Total must equal exactly 100 points.
            </p>
          </div>
          <div
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold ${
              isConfigValid
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "bg-red-50 text-red-700 border border-red-200"
            }`}
          >
            <span>Total: {configTotal} / 100 pts</span>
            {isConfigValid ? "✓ Valid" : "✗ Must equal 100"}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">
              Must-Have Skills
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                disabled={isLocked}
                value={scoringConfig.must_have_skills}
                onChange={(e) => updateConfig("must_have_skills", Number(e.target.value))}
                className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-2.5 py-1.5 disabled:bg-slate-50"
              />
              <span className="absolute right-2 top-2 text-[10px] text-slate-400">pts</span>
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">
              Experience
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                disabled={isLocked}
                value={scoringConfig.experience}
                onChange={(e) => updateConfig("experience", Number(e.target.value))}
                className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-2.5 py-1.5 disabled:bg-slate-50"
              />
              <span className="absolute right-2 top-2 text-[10px] text-slate-400">pts</span>
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">
              Notice Period
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                disabled={isLocked}
                value={scoringConfig.notice_period}
                onChange={(e) => updateConfig("notice_period", Number(e.target.value))}
                className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-2.5 py-1.5 disabled:bg-slate-50"
              />
              <span className="absolute right-2 top-2 text-[10px] text-slate-400">pts</span>
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">
              Location
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                disabled={isLocked}
                value={scoringConfig.location}
                onChange={(e) => updateConfig("location", Number(e.target.value))}
                className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-2.5 py-1.5 disabled:bg-slate-50"
              />
              <span className="absolute right-2 top-2 text-[10px] text-slate-400">pts</span>
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-600 mb-1">
              Nice-To-Have Skills
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                disabled={isLocked}
                value={scoringConfig.nice_to_have_skills}
                onChange={(e) => updateConfig("nice_to_have_skills", Number(e.target.value))}
                className="w-full text-xs font-semibold border border-slate-300 rounded-lg px-2.5 py-1.5 disabled:bg-slate-50"
              />
              <span className="absolute right-2 top-2 text-[10px] text-slate-400">pts</span>
            </div>
          </div>
        </div>
      </div>

      {/* Criteria Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h4 className="font-semibold text-slate-800 text-sm">
              3. Evaluation Criteria ({criteria.length})
            </h4>
            <p className="text-xs text-slate-500">
              Skills, qualifications, and domain criteria to evaluate candidate profiles against.
            </p>
          </div>
          {!isLocked && (
            <button
              type="button"
              onClick={addCriterion}
              className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
            >
              + Add Criterion
            </button>
          )}
        </div>

        {criteria.length === 0 ? (
          <div className="py-8 text-center text-slate-400 text-xs">
            No criteria configured yet. Click &ldquo;+ Add Criterion&rdquo; or extract from JD above.
          </div>
        ) : (
          <div className="space-y-3">
            {criteria.map((crit, idx) => (
              <div
                key={idx}
                className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 hover:bg-white transition-colors space-y-2"
              >
                <div className="grid grid-cols-12 gap-2 items-center">
                  {/* Reorder buttons */}
                  {!isLocked && (
                    <div className="col-span-1 flex flex-col gap-0.5">
                      <button
                        type="button"
                        onClick={() => moveCriterion(idx, "up")}
                        disabled={idx === 0}
                        className="text-[10px] text-slate-400 hover:text-slate-700 disabled:opacity-20"
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        onClick={() => moveCriterion(idx, "down")}
                        disabled={idx === criteria.length - 1}
                        className="text-[10px] text-slate-400 hover:text-slate-700 disabled:opacity-20"
                      >
                        ▼
                      </button>
                    </div>
                  )}

                  {/* Type */}
                  <div className={isLocked ? "col-span-3" : "col-span-3"}>
                    <select
                      disabled={isLocked}
                      value={crit.criterion_type}
                      onChange={(e) => updateCriterion(idx, { criterion_type: e.target.value })}
                      className="w-full text-xs border border-slate-300 rounded px-2 py-1.5 bg-white disabled:bg-slate-100"
                    >
                      <option value="must_have_skill">Must-Have Skill</option>
                      <option value="nice_to_have_skill">Nice-To-Have Skill</option>
                      <option value="experience">Experience</option>
                      <option value="notice_period">Notice Period</option>
                      <option value="location">Location</option>
                      <option value="additional">Additional / Education</option>
                    </select>
                  </div>

                  {/* Name */}
                  <div className={isLocked ? "col-span-4" : "col-span-4"}>
                    <input
                      type="text"
                      disabled={isLocked}
                      value={crit.criterion_name}
                      onChange={(e) =>
                        updateCriterion(idx, {
                          criterion_name: e.target.value,
                          label: e.target.value,
                        })
                      }
                      placeholder="Criterion name (e.g. Java, Spring Boot)"
                      className="w-full text-xs border border-slate-300 rounded px-2.5 py-1.5 bg-white disabled:bg-slate-100 font-medium"
                    />
                  </div>

                  {/* Weight */}
                  <div className="col-span-2">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      disabled={isLocked}
                      value={crit.weight}
                      onChange={(e) =>
                        updateCriterion(idx, { weight: Number(e.target.value) })
                      }
                      placeholder="Weight"
                      className="w-full text-xs border border-slate-300 rounded px-2 py-1.5 bg-white disabled:bg-slate-100"
                    />
                  </div>

                  {/* Mandatory Checkbox */}
                  <div className="col-span-1 text-center">
                    <label className="inline-flex items-center gap-1 text-[11px] text-slate-600 cursor-pointer">
                      <input
                        type="checkbox"
                        disabled={isLocked}
                        checked={crit.is_mandatory}
                        onChange={(e) =>
                          updateCriterion(idx, { is_mandatory: e.target.checked })
                        }
                        className="rounded border-slate-300 text-indigo-600 focus:ring-0"
                      />
                      Req
                    </label>
                  </div>

                  {/* Delete button */}
                  {!isLocked && (
                    <div className="col-span-1 text-right">
                      <button
                        type="button"
                        onClick={() => removeCriterion(idx)}
                        className="text-red-500 hover:text-red-700 text-xs px-2 py-1 rounded hover:bg-red-50"
                      >
                        ✕
                      </button>
                    </div>
                  )}
                </div>

                {/* Evidence text */}
                <div className="text-xs">
                  <input
                    type="text"
                    disabled={isLocked}
                    value={crit.evidence_from_jd ?? ""}
                    onChange={(e) =>
                      updateCriterion(idx, { evidence_from_jd: e.target.value })
                    }
                    placeholder="Evidence excerpt from job description (optional)"
                    className="w-full text-[11px] text-slate-600 italic border border-slate-200 rounded px-2.5 py-1 bg-white/70 disabled:bg-slate-100"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {!isLocked && (
        <div className="flex items-center justify-end gap-3 pt-2">
          {onSaveDraft && (
            <button
              type="button"
              disabled={saving || isLoading}
              onClick={handleSaveDraft}
              className="text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 px-4 py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save as Draft"}
            </button>
          )}
          {onApprove && (
            <button
              type="button"
              disabled={saving || isLoading || !isConfigValid}
              onClick={handleApprove}
              className="text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              {saving ? "Processing..." : "Approve & Publish Scorecard"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

