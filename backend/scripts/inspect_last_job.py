import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_session_factory
from app.models.resume import ResumeProcessingJob, Resume, UploadBatch
from app.models.candidate import Candidate
from sqlalchemy import select, func

async def main():
    async with async_session_factory() as db:
        nj = await db.execute(select(func.count(ResumeProcessingJob.id)))
        nr = await db.execute(select(func.count(Resume.id)))
        nb = await db.execute(select(func.count(UploadBatch.id)))
        nc = await db.execute(select(func.count(Candidate.id)))
        print(f"Jobs: {nj.scalar_one()}, Resumes: {nr.scalar_one()}, Batches: {nb.scalar_one()}, Candidates: {nc.scalar_one()}")

if __name__ == "__main__":
    asyncio.run(main())
