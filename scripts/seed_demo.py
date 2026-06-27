"""
scripts/seed_demo.py
─────────────────────
Seeds the database with demo data for ExamIQ.

Creates:
  - 1 faculty user   (faculty@itu.edu.pk / Faculty@123)
  - 1 student user   (student@itu.edu.pk / Student@123)
  - 50 COA exam items with IRT parameters
  - 1 published exam (Computer Architecture Mid-Term)

Run:
    python scripts/seed_demo.py

Safe to run multiple times (skips existing data).
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.security import hash_password
from src.core.settings import settings
from src.db.models import Exam, ExamItem, User

# ── Demo Items Bank (50 COA questions) ─────────────────────────────
COA_ITEMS = [
    # Pipeline & Hazards
    {
        "topic": "Pipeline Hazards",
        "content": "Which type of pipeline hazard occurs when an instruction depends on the result of a previous instruction that has not yet completed?",
        "options": ["Structural hazard", "Data hazard", "Control hazard", "Resource hazard"],
        "correct": 1, "b": -0.5, "a": 1.2,
    },
    {
        "topic": "Pipeline Hazards",
        "content": "Load-use hazard in a 5-stage pipeline requires how many stall cycles?",
        "options": ["0", "1", "2", "3"],
        "correct": 1, "b": 0.3, "a": 1.5,
    },
    {
        "topic": "Pipeline",
        "content": "Forwarding (bypassing) in a RISC-V pipeline is used to resolve which type of hazard without stalling?",
        "options": ["Control hazards", "Structural hazards", "Data hazards", "Memory hazards"],
        "correct": 2, "b": -0.8, "a": 1.1,
    },
    {
        "topic": "Pipeline",
        "content": "In a 5-stage RISC pipeline, branch decision is made at which stage?",
        "options": ["IF", "ID", "EX", "MEM"],
        "correct": 2, "b": 0.5, "a": 1.4,
    },
    {
        "topic": "Pipeline",
        "content": "What is the CPI of an ideal pipelined processor (no hazards, no stalls)?",
        "options": ["0", "1", "n (pipeline stages)", "Depends on ISA"],
        "correct": 1, "b": -1.2, "a": 0.9,
    },
    # Cache Memory
    {
        "topic": "Cache Memory",
        "content": "In a direct-mapped cache, if we have 16KB cache with 32-byte blocks, how many cache sets are there?",
        "options": ["256", "512", "1024", "2048"],
        "correct": 1, "b": 1.2, "a": 1.8,
    },
    {
        "topic": "Cache Memory",
        "content": "AMAT (Average Memory Access Time) = ?",
        "options": [
            "Hit time + Miss rate × Miss penalty",
            "Hit rate × Hit time",
            "Miss rate × Miss penalty",
            "Hit time × Miss penalty",
        ],
        "correct": 0, "b": -0.3, "a": 1.3,
    },
    {
        "topic": "Cache Memory",
        "content": "Which cache replacement policy replaces the block that was least recently used?",
        "options": ["FIFO", "Random", "LRU", "MRU"],
        "correct": 2, "b": -1.5, "a": 0.8,
    },
    {
        "topic": "Cache Memory",
        "content": "A 2-way set-associative cache has how many valid bits per set?",
        "options": ["1", "2", "4", "Depends on block size"],
        "correct": 1, "b": 0.8, "a": 1.6,
    },
    {
        "topic": "Cache Memory",
        "content": "What does spatial locality mean in the context of memory access?",
        "options": [
            "Recently accessed data will be accessed again soon",
            "Data near recently accessed locations will be accessed soon",
            "All cache misses occur at random locations",
            "Cache hit rate is always above 90%",
        ],
        "correct": 1, "b": -0.9, "a": 1.0,
    },
    # Memory Hierarchy
    {
        "topic": "Virtual Memory",
        "content": "In virtual memory, a TLB miss means?",
        "options": [
            "The page is not in main memory",
            "The page table entry is not cached in TLB",
            "The physical address is invalid",
            "A page fault has occurred",
        ],
        "correct": 1, "b": 1.0, "a": 1.7,
    },
    {
        "topic": "Virtual Memory",
        "content": "Page fault handling requires saving program state and loading the missing page from?",
        "options": ["Cache", "TLB", "Disk/Secondary Storage", "Registers"],
        "correct": 2, "b": -0.6, "a": 1.1,
    },
    {
        "topic": "Virtual Memory",
        "content": "What is the size of a virtual address space with 32-bit addressing?",
        "options": ["2GB", "4GB", "8GB", "16GB"],
        "correct": 1, "b": -0.4, "a": 1.2,
    },
    # ILP & Superscalar
    {
        "topic": "ILP",
        "content": "Tomasulo's algorithm uses which structure to track instruction dependencies?",
        "options": ["Scoreboard", "Reservation Stations", "Instruction Queue", "Reorder Buffer only"],
        "correct": 1, "b": 1.5, "a": 1.9,
    },
    {
        "topic": "ILP",
        "content": "Out-of-order execution commits instructions in-order to maintain correctness using?",
        "options": ["Reorder Buffer (ROB)", "Reservation Stations", "Register File", "Data Cache"],
        "correct": 0, "b": 1.3, "a": 1.7,
    },
    {
        "topic": "ILP",
        "content": "Which technique removes WAR (Write After Read) hazards using renamed registers?",
        "options": ["Forwarding", "Speculative execution", "Register renaming", "Branch prediction"],
        "correct": 2, "b": 1.8, "a": 2.0,
    },
    {
        "topic": "ILP",
        "content": "A superscalar processor can issue how many instructions per cycle?",
        "options": ["Exactly 1", "Exactly 2", "More than 1", "Depends on pipeline depth"],
        "correct": 2, "b": -0.7, "a": 1.1,
    },
    # RISC-V ISA
    {
        "topic": "RISC-V ISA",
        "content": "In RISC-V, the instruction `addi x1, x0, 5` stores what value in x1?",
        "options": ["0", "5", "x0+5=5", "Undefined"],
        "correct": 1, "b": -2.0, "a": 0.7,
    },
    {
        "topic": "RISC-V ISA",
        "content": "The RISC-V `jalr` instruction is used for?",
        "options": ["Conditional branches", "Indirect jumps", "Load operations", "Memory fences"],
        "correct": 1, "b": 0.2, "a": 1.3,
    },
    {
        "topic": "RISC-V ISA",
        "content": "How many general-purpose registers does the base RISC-V (RV32I) have?",
        "options": ["8", "16", "32", "64"],
        "correct": 2, "b": -1.8, "a": 0.8,
    },
    {
        "topic": "RISC-V ISA",
        "content": "The RISC-V store-word instruction `sw x2, 8(x3)` stores?",
        "options": [
            "x3 into memory at address x2+8",
            "x2 into memory at address x3+8",
            "8 into register x2",
            "x2+x3 into memory at offset 8",
        ],
        "correct": 1, "b": 0.6, "a": 1.5,
    },
    # Branch Prediction
    {
        "topic": "Branch Prediction",
        "content": "A 1-bit branch predictor's main weakness is?",
        "options": [
            "It requires too much hardware",
            "It mispredicts twice at loop boundaries",
            "It cannot predict backward branches",
            "It only works for unconditional branches",
        ],
        "correct": 1, "b": 1.0, "a": 1.6,
    },
    {
        "topic": "Branch Prediction",
        "content": "A 2-bit saturating counter branch predictor changes prediction after how many consecutive mispredictions?",
        "options": ["1", "2", "3", "4"],
        "correct": 1, "b": 0.9, "a": 1.5,
    },
    {
        "topic": "Branch Prediction",
        "content": "The Branch Target Buffer (BTB) stores?",
        "options": [
            "Branch instruction opcodes",
            "Predicted target addresses for branch instructions",
            "History of all branch outcomes",
            "Return addresses for function calls",
        ],
        "correct": 1, "b": 0.7, "a": 1.4,
    },
    # I/O and Interrupts
    {
        "topic": "I/O",
        "content": "Direct Memory Access (DMA) transfers data without involving?",
        "options": ["Memory controller", "I/O device", "CPU", "System bus"],
        "correct": 2, "b": -0.8, "a": 1.1,
    },
    {
        "topic": "I/O",
        "content": "In interrupt-driven I/O, what saves the processor state before handling an interrupt?",
        "options": ["The I/O device", "The interrupt service routine", "Hardware automatically", "The OS scheduler"],
        "correct": 2, "b": 0.4, "a": 1.3,
    },
    {
        "topic": "I/O",
        "content": "Polling (busy waiting) for I/O is inefficient because?",
        "options": [
            "It requires additional hardware",
            "The CPU wastes cycles checking device status",
            "It only works for keyboard input",
            "It requires DMA support",
        ],
        "correct": 1, "b": -1.0, "a": 1.0,
    },
    # Performance
    {
        "topic": "Performance",
        "content": "Amdahl's Law states that the speedup from improving a fraction f of a system is limited by?",
        "options": ["1/f", "1/(1-f)", "f × speedup", "1/(1-f + f/speedup)"],
        "correct": 3, "b": 1.6, "a": 1.8,
    },
    {
        "topic": "Performance",
        "content": "CPU execution time = ?",
        "options": [
            "Instruction count × CPI",
            "Instruction count × CPI × Clock cycle time",
            "Clock frequency / CPI",
            "Instruction count / Clock frequency",
        ],
        "correct": 1, "b": 0.1, "a": 1.2,
    },
    {
        "topic": "Performance",
        "content": "MIPS (Million Instructions Per Second) is a misleading performance metric because?",
        "options": [
            "It doesn't account for instruction complexity or ISA differences",
            "It is always higher than real performance",
            "It only measures integer performance",
            "Modern CPUs execute fewer than 1 MIPS",
        ],
        "correct": 0, "b": 0.8, "a": 1.4,
    },
    # Datapath
    {
        "topic": "Datapath",
        "content": "In a single-cycle RISC-V datapath, the ALU control unit inputs are?",
        "options": [
            "opcode only",
            "ALUOp and funct3/funct7 fields",
            "Register values and immediate",
            "PC and instruction memory output",
        ],
        "correct": 1, "b": 0.9, "a": 1.5,
    },
    {
        "topic": "Datapath",
        "content": "The Program Counter (PC) in a pipelined processor is updated how many times per instruction?",
        "options": ["Once", "Once per pipeline stage", "Only after writeback", "Never — it's static"],
        "correct": 0, "b": -0.5, "a": 1.1,
    },
    {
        "topic": "Datapath",
        "content": "Sign extension in RISC-V is required when?",
        "options": [
            "Converting 5-bit register addresses to 32-bit",
            "Using I-type 12-bit immediates in 32-bit operations",
            "Reading from the register file",
            "Writing results back to memory",
        ],
        "correct": 1, "b": 0.6, "a": 1.3,
    },
    # Advanced Topics
    {
        "topic": "SIMD",
        "content": "SIMD (Single Instruction Multiple Data) improves performance by?",
        "options": [
            "Running multiple programs simultaneously",
            "Applying one operation to multiple data elements in parallel",
            "Increasing clock frequency",
            "Reducing instruction count through macro-ops",
        ],
        "correct": 1, "b": 0.2, "a": 1.2,
    },
    {
        "topic": "Memory",
        "content": "DRAM (Dynamic RAM) requires periodic refresh because?",
        "options": [
            "It uses flip-flops that need synchronization",
            "Capacitors leak charge over time",
            "It operates at a different voltage than CPU",
            "Data is stored optically and fades",
        ],
        "correct": 1, "b": -0.9, "a": 1.0,
    },
    {
        "topic": "Exceptions",
        "content": "In RISC-V, the `mepc` CSR register stores?",
        "options": [
            "The machine mode exception cause",
            "The address of the instruction that caused the exception",
            "The trap vector base address",
            "The machine mode status flags",
        ],
        "correct": 1, "b": 1.7, "a": 2.0,
    },
    {
        "topic": "Pipeline",
        "content": "Flushing the pipeline after a mispredicted branch wastes how many cycles in a 5-stage pipeline where branch is resolved at EX stage?",
        "options": ["1", "2", "3", "4"],
        "correct": 1, "b": 1.1, "a": 1.6,
    },
    {
        "topic": "Cache Memory",
        "content": "Write-back cache policy writes to main memory?",
        "options": [
            "On every write operation",
            "Only when the dirty block is evicted",
            "Every N write operations",
            "Synchronously with every CPU cycle",
        ],
        "correct": 1, "b": 0.3, "a": 1.3,
    },
    {
        "topic": "ILP",
        "content": "The number of instructions that can execute simultaneously in a superscalar processor is called?",
        "options": ["Pipeline depth", "Issue width", "CPI", "IPC"],
        "correct": 1, "b": 1.2, "a": 1.7,
    },
    {
        "topic": "RISC-V ISA",
        "content": "Which RISC-V instruction format is used for load instructions (e.g., lw)?",
        "options": ["R-type", "I-type", "S-type", "B-type"],
        "correct": 1, "b": 0.4, "a": 1.2,
    },
    {
        "topic": "RISC-V ISA",
        "content": "The `beq x1, x2, label` instruction branches if?",
        "options": ["x1 > x2", "x1 != x2", "x1 == x2", "x1 < x2"],
        "correct": 2, "b": -2.0, "a": 0.7,
    },
    {
        "topic": "Performance",
        "content": "Reducing CPI by 20% and clock cycle time by 10% gives overall speedup of approximately?",
        "options": ["30%", "28%", "22%", "10%"],
        "correct": 1, "b": 1.4, "a": 1.8,
    },
    {
        "topic": "Cache Memory",
        "content": "A fully-associative cache has how many sets?",
        "options": ["1", "2", "Number of blocks", "Number of ways"],
        "correct": 0, "b": 1.0, "a": 1.5,
    },
    {
        "topic": "Virtual Memory",
        "content": "Thrashing occurs when?",
        "options": [
            "TLB hit rate drops below 50%",
            "Processes spend more time swapping pages than executing",
            "Cache miss rate exceeds miss penalty",
            "Branch misprediction rate exceeds 50%",
        ],
        "correct": 1, "b": 0.6, "a": 1.3,
    },
    {
        "topic": "Pipeline",
        "content": "Which pipeline stage reads from the register file in a standard RISC-V 5-stage pipeline?",
        "options": ["IF", "ID", "EX", "WB"],
        "correct": 1, "b": -1.3, "a": 0.9,
    },
    {
        "topic": "Exceptions",
        "content": "In RISC-V, which privilege mode has the highest level of hardware access?",
        "options": ["User mode", "Supervisor mode", "Machine mode", "Hypervisor mode"],
        "correct": 2, "b": 0.0, "a": 1.2,
    },
    {
        "topic": "ILP",
        "content": "VLIW (Very Long Instruction Word) architectures rely on which component to find ILP?",
        "options": [
            "Hardware scheduler at runtime",
            "Compiler at compile time",
            "Operating system at load time",
            "Branch predictor at decode stage",
        ],
        "correct": 1, "b": 1.9, "a": 2.1,
    },
    {
        "topic": "Datapath",
        "content": "The Writeback (WB) stage of a RISC-V pipeline writes results to?",
        "options": ["Data memory", "Instruction memory", "Register file", "Program Counter"],
        "correct": 2, "b": -1.6, "a": 0.8,
    },
    {
        "topic": "Performance",
        "content": "Iron Law of Performance: CPU time = Instructions × CPI × ___?",
        "options": ["Frequency", "Clock cycle time", "Pipeline stages", "Cache hit rate"],
        "correct": 1, "b": -0.2, "a": 1.1,
    },
    {
        "topic": "Branch Prediction",
        "content": "A Return Address Stack (RAS) is used to predict targets of?",
        "options": ["Conditional branches", "Unconditional jumps", "Function return instructions", "System calls"],
        "correct": 2, "b": 1.4, "a": 1.8,
    },
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        print("\n🌱 ExamIQ Seed Script Starting...\n")

        # ── 1. Create Faculty User ────────────────────────────────
        existing_faculty = await db.execute(
            select(User).where(User.email == "faculty@itu.edu.pk")
        )
        faculty = existing_faculty.scalar_one_or_none()
        if not faculty:
            faculty = User(
                email="faculty@itu.edu.pk",
                hashed_password=hash_password("Faculty@123"),
                full_name="Dr. Ahmed Khan",
                role="faculty",
                is_active=True,
            )
            db.add(faculty)
            await db.flush()
            print("✅ Faculty user created: faculty@itu.edu.pk / Faculty@123")
        else:
            print("⏭️  Faculty user already exists")

        # ── 2. Create Student User ────────────────────────────────
        existing_student = await db.execute(
            select(User).where(User.email == "student@itu.edu.pk")
        )
        student = existing_student.scalar_one_or_none()
        if not student:
            student = User(
                email="student@itu.edu.pk",
                hashed_password=hash_password("Student@123"),
                full_name="Daniyal Ahmed",
                role="student",
                is_active=True,
            )
            db.add(student)
            await db.flush()
            print("✅ Student user created: student@itu.edu.pk / Student@123")
        else:
            print("⏭️  Student user already exists")

        # ── 3. Create Exam Items ──────────────────────────────────
        existing_items = await db.execute(
            select(ExamItem).where(ExamItem.subject == "COA")
        )
        existing_count = len(existing_items.scalars().all())

        if existing_count < 10:
            items_created = 0
            for item_data in COA_ITEMS:
                item = ExamItem(
                    subject="COA",
                    topic=item_data["topic"],
                    content=item_data["content"],
                    item_type="mcq",
                    options={"choices": item_data["options"]},
                    correct_option=item_data["correct"],
                    irt_a=item_data.get("a", 1.0),
                    irt_b=item_data.get("b", 0.0),
                    irt_c=0.25,
                    irt_calibrated=True,
                    created_by=faculty.id,
                )
                db.add(item)
                items_created += 1

            await db.flush()
            print(f"✅ {items_created} COA exam items created with IRT parameters")
        else:
            print(f"⏭️  {existing_count} COA items already exist")

        # ── 4. Create Exam ────────────────────────────────────────
        existing_exam = await db.execute(
            select(Exam).where(Exam.title == "Computer Architecture Mid-Term — CE24")
        )
        exam = existing_exam.scalar_one_or_none()
        if not exam:
            exam = Exam(
                title="Computer Architecture Mid-Term — CE24",
                subject="COA",
                max_items=30,
                time_limit_minutes=60,
                is_adaptive=True,
                created_by=faculty.id,
                status="active",
            )
            db.add(exam)
            await db.flush()
            print(f"✅ Exam created and published: '{exam.title}'")
            print(f"   Exam ID: {exam.id}")
        else:
            print(f"⏭️  Exam already exists: '{exam.title}'")

        await db.commit()
        print("\n🎉 Seed complete!\n")
        print("=" * 55)
        print("Demo credentials:")
        print("  Faculty  → faculty@itu.edu.pk / Faculty@123")
        print("  Student  → student@itu.edu.pk / Student@123")
        print("=" * 55)
        print("\nNext steps:")
        print("  1. Open http://localhost:3000")
        print("  2. Login as student → take the COA exam")
        print("  3. Login as faculty → view analytics + flags")
        print("  4. Run: python scripts/seed_demo.py --more-students")
        print("     to seed 10 more students for collusion testing\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())