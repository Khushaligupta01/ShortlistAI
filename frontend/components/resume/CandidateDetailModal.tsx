"use client";

import { useEffect, useState } from "react";
import {
  X,
  Briefcase,
  GraduationCap,
  Award,
  Download,
  AlertTriangle,
  MapPin,
  Edit2,
  Save,
} from "lucide-react";
import { api } from "@/lib/api";
import type { CandidateDetail } from "@/lib/types";

interface CandidateDetailModalProps {
  candidateId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onCandidateUpdated?: () => void;
}

export default function CandidateDetailModal({
  candidateId,
  isOpen,
  onClose,
  onCandidateUpdated,
}: CandidateDetailModalProps) {
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  // Recruiter edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    location: "",
    notice_period_days: "",
    skills: "",
  });
  const [saveLoading, setSaveLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !candidateId) {
      setCandidate(null);
      setIsEditing(false);
      return;
    }

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getCandidateDetail(candidateId!);
        setCandidate(data);
        setEditForm({
          full_name: data.full_name || "",
          email: data.email || "",
          phone: data.phone || "",
          location: data.location || "",
          notice_period_days: data.notice_period_days !== null && data.notice_period_days !== undefined
            ? String(data.notice_period_days)
            : "",
          skills: data.skills.map((s) => s.raw_name).join(", "),
        });
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load candidate details.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isOpen, candidateId]);

  if (!isOpen) return null;

  async function handleDownloadResume(resumeId: string) {
    setDownloading(true);
    try {
      const { blob, filename } = await api.downloadResumeDocument(resumeId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to download document.");
    } finally {
      setDownloading(false);
    }
  }

  async function handleSaveReview() {
    if (!candidate || candidate.resumes.length === 0) return;
    setSaveLoading(true);
    try {
      const resumeId = candidate.resumes[0].id;
      const skillsArray = editForm.skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      await api.reviewResume(resumeId, {
        full_name: editForm.full_name || null,
        email: editForm.email || null,
        phone: editForm.phone || null,
        location: editForm.location || null,
        notice_period_days: editForm.notice_period_days ? Number(editForm.notice_period_days) : null,
        skills: skillsArray,
      });

      // Reload updated candidate data
      const updated = await api.getCandidateDetail(candidate.id);
      setCandidate(updated);
      setIsEditing(false);
      onCandidateUpdated?.();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to save recruiter updates.");
    } finally {
      setSaveLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#292722]/50 backdrop-blur-xs p-4">
      <div className="bg-[#FFFFFF] rounded-2xl shadow-2xl w-full max-w-3xl overflow-hidden border border-[#E8E2D8] animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[90vh] text-[#292722]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[#E8E2D8] flex items-center justify-between bg-[#F5F1EA]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#756653] text-[#FAF9F6] font-bold flex items-center justify-center text-sm shadow-sm">
              {candidate?.full_name ? candidate.full_name.charAt(0).toUpperCase() : "C"}
            </div>
            <div>
              <h2 className="text-base font-serif font-bold text-[#292722]">
                {candidate?.full_name || "Candidate Profile"}
              </h2>
              <p className="text-xs text-[#6F6A61]">
                Structured Candidate Extraction Record • ShortlistAI
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!isEditing && candidate && (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="text-xs font-semibold text-[#292722] bg-[#FFFFFF] border border-[#D9D1C5] hover:bg-[#FAF9F6] px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors shadow-sm"
              >
                <Edit2 className="w-3.5 h-3.5 text-[#756653]" />
                Review / Edit
              </button>
            )}
            <button
              onClick={onClose}
              className="text-[#918A80] hover:text-[#292722] p-1.5 rounded-lg hover:bg-[#EEE8DD] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1 text-xs text-[#6F6A61]">
          {loading ? (
            <div className="py-12 text-center text-[#918A80]">Loading candidate profile...</div>
          ) : error ? (
            <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] p-4 rounded-xl font-medium">
              {error}
            </div>
          ) : candidate ? (
            <>
              {/* Recruiter Edit Form */}
              {isEditing ? (
                <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[#E8E2D8] font-serif font-bold text-[#292722]">
                    <span>Recruiter Candidate Review & Corrections</span>
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      className="text-[#756653] hover:underline text-[11px]"
                    >
                      Cancel Edit
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="font-semibold text-[#292722] block mb-1">Full Name</label>
                      <input
                        type="text"
                        value={editForm.full_name}
                        onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                        className="w-full bg-[#FFFFFF] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-[#292722] block mb-1">Email</label>
                      <input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                        className="w-full bg-[#FFFFFF] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-[#292722] block mb-1">Phone</label>
                      <input
                        type="text"
                        value={editForm.phone}
                        onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                        className="w-full bg-[#FFFFFF] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-[#292722] block mb-1">Location</label>
                      <input
                        type="text"
                        value={editForm.location}
                        onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                        className="w-full bg-[#FFFFFF] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-[#292722] block mb-1">Notice Period (Days)</label>
                      <input
                        type="number"
                        value={editForm.notice_period_days}
                        onChange={(e) => setEditForm({ ...editForm, notice_period_days: e.target.value })}
                        className="w-full bg-[#FFFFFF] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                        placeholder="e.g. 30 (0 for immediate)"
                      />
                    </div>
                    <div>
                      <label className="font-semibold text-[#292722] block mb-1">Skills (Comma separated)</label>
                      <input
                        type="text"
                        value={editForm.skills}
                        onChange={(e) => setEditForm({ ...editForm, skills: e.target.value })}
                        className="w-full bg-[#FFFFFF] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                        placeholder="Java, Spring Boot, Kafka..."
                      />
                    </div>
                  </div>
                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      disabled={saveLoading}
                      onClick={handleSaveReview}
                      className="bg-[#756653] hover:bg-[#5F5243] text-white font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-sm disabled:opacity-50 transition"
                    >
                      <Save className="w-3.5 h-3.5" />
                      {saveLoading ? "Saving..." : "Save Corrections"}
                    </button>
                  </div>
                </div>
              ) : null}

              {/* Overview & Contact Card */}
              <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <span className="text-[11px] font-medium text-[#6F6A61] uppercase tracking-wider block">
                    Total Experience
                  </span>
                  <span className="text-sm font-serif font-bold text-[#292722] mt-0.5 block">
                    {candidate.total_experience_years !== null && candidate.total_experience_years !== undefined
                      ? `${candidate.total_experience_years} Years`
                      : "Not specified"}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-[#6F6A61] uppercase tracking-wider block">
                    Notice Period
                  </span>
                  <span className="text-sm font-serif font-bold text-[#292722] mt-0.5 block">
                    {candidate.notice_period_days !== null && candidate.notice_period_days !== undefined
                      ? candidate.notice_period_days === 0
                        ? "Immediate Joiner"
                        : `${candidate.notice_period_days} Days`
                      : "Unknown / Not stated"}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-[#6F6A61] uppercase tracking-wider block">
                    Location
                  </span>
                  <span className="text-sm font-serif font-bold text-[#292722] mt-0.5 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-[#756653]" />
                    {candidate.location || "Unspecified"}
                  </span>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-[#6F6A61] uppercase tracking-wider block">
                    Contact Access
                  </span>
                  <span className="text-xs font-semibold text-[#292722] mt-0.5 block truncate">
                    {candidate.email || "No email"}
                  </span>
                  {candidate.phone && (
                    <span className="text-[11px] text-[#6F6A61] block truncate">
                      {candidate.phone}
                    </span>
                  )}
                </div>
              </div>

              {/* Extraction Warnings & Missing Fields */}
              {candidate.parsed_profile_json?.warnings &&
                candidate.parsed_profile_json.warnings.length > 0 && (
                  <div className="bg-[#FDF6E7] border border-[#F1DCAC] rounded-xl p-3 text-xs text-[#7A5212] space-y-1">
                    <div className="font-bold flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-[#7A5212]" />
                      Extraction Notes & Ambiguities:
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] pl-1">
                      {candidate.parsed_profile_json.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

              {/* Skills With Evidence */}
              <div className="space-y-2">
                <h3 className="font-serif font-bold text-[#292722] text-sm flex items-center gap-2">
                  <Award className="w-4 h-4 text-[#756653]" />
                  Extracted Skills ({candidate.skills.length})
                </h3>
                {candidate.skills.length === 0 ? (
                  <p className="text-[#918A80] italic">No explicit skills extracted.</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {candidate.skills.map((skill) => (
                      <div
                        key={skill.id}
                        className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl p-2.5 hover:border-[#D9D1C5] transition-colors shadow-sm"
                      >
                        <div className="font-semibold text-[#292722]">{skill.raw_name}</div>
                        {skill.evidence && (
                          <p className="text-[11px] text-[#6F6A61] italic mt-1 line-clamp-2">
                            &ldquo;{skill.evidence}&rdquo;
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Employment History Timeline */}
              <div className="space-y-2">
                <h3 className="font-serif font-bold text-[#292722] text-sm flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-[#756653]" />
                  Employment History ({candidate.employments.length})
                </h3>
                {candidate.employments.length === 0 ? (
                  <p className="text-[#918A80] italic">No employment records parsed.</p>
                ) : (
                  <div className="border border-[#E8E2D8] rounded-xl divide-y divide-[#EFEAE2] bg-[#FFFFFF]">
                    {candidate.employments.map((emp) => (
                      <div key={emp.id} className="p-3.5 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[#292722] text-xs">{emp.job_title}</span>
                          <span className="text-[11px] text-[#918A80] font-medium">
                            {emp.start_date || "Unknown"} – {emp.end_date || (emp.is_current ? "Present" : "Unknown")}
                          </span>
                        </div>
                        <div className="text-[#756653] font-medium">{emp.company}</div>
                        {emp.description && (
                          <p className="text-[#6F6A61] text-[11px] whitespace-pre-line leading-relaxed">
                            {emp.description}
                          </p>
                        )}
                        {emp.technologies && emp.technologies.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {emp.technologies.map((t, idx) => (
                              <span
                                key={idx}
                                className="bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] px-1.5 py-0.5 rounded text-[10px]"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Education */}
              <div className="space-y-2">
                <h3 className="font-serif font-bold text-[#292722] text-sm flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-[#756653]" />
                  Education ({candidate.educations.length})
                </h3>
                {candidate.educations.length === 0 ? (
                  <p className="text-[#918A80] italic">No education records parsed.</p>
                ) : (
                  <div className="border border-[#E8E2D8] rounded-xl divide-y divide-[#EFEAE2] bg-[#FFFFFF]">
                    {candidate.educations.map((edu) => (
                      <div key={edu.id} className="p-3 flex items-center justify-between">
                        <div>
                          <div className="font-bold text-[#292722]">{edu.institution}</div>
                          <div className="text-[#6F6A61] text-[11px]">
                            {edu.qualification}
                            {edu.field_of_study ? ` in ${edu.field_of_study}` : ""}
                          </div>
                        </div>
                        {edu.graduation_year && (
                          <span className="text-[11px] font-semibold text-[#292722] bg-[#F5F1EA] border border-[#E8E2D8] px-2 py-0.5 rounded">
                            {edu.graduation_year}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Attached Resumes & Downloads */}
              <div className="space-y-2 pt-2">
                <h3 className="font-serif font-bold text-[#292722] text-sm">Resume Documents</h3>
                <div className="flex flex-wrap gap-2">
                  {candidate.resumes.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      disabled={downloading}
                      onClick={() => handleDownloadResume(r.id)}
                      className="inline-flex items-center gap-2 bg-[#F5F1EA] hover:bg-[#EEE8DD] text-[#292722] px-3 py-1.5 rounded-xl font-medium transition-colors border border-[#D9D1C5] disabled:opacity-50 text-xs shadow-sm"
                    >
                      <Download className="w-3.5 h-3.5 text-[#756653]" />
                      {r.file_name} ({Math.round(r.file_size_bytes / 1024)} KB)
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-[#F5F1EA] border-t border-[#E8E2D8] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold text-[#6F6A61] hover:text-[#292722] rounded-lg hover:bg-[#EEE8DD] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
