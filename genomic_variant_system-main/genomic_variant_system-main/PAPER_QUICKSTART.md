# ClinX Clinical - IEEE Paper Writing Quickstart

## 📁 Project Structure Created

```
genomic_variant_system-main/
├── IEEE_PAPER_OUTLINE.md       # Detailed section-by-section outline
├── clinx_clinical_paper.tex    # LaTeX template (IEEEtran format)
├── references.bib              # 30+ key references in BibTeX
├── run_benchmark.py            # CLI entry point
├── benchmark_runner.py         # Core benchmark logic
├── benchmark_results/          # Generated results (after running)
└── sample_research_paper.pdf   # Reference IEEE paper (GestureHeal)
```

---

## 🚀 Quick Start: Generate Paper Data

### 1. Start Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
# Server runs on http://localhost:8000
```

### 2. Run Benchmark (generates Tables V-VIII data)
```bash
# Full 50-variant benchmark (~3-5 minutes)
python run_benchmark.py

# Quick test (5 variants, ~30 seconds)
python run_benchmark.py --quick

# Custom output directory
python run_benchmark.py --output my_paper_results
```

### 3. Check Results
```bash
ls benchmark_results/
# clinx_results_YYYYMMDD_HHMMSS.json  - Raw results
# clinx_results_YYYYMMDD_HHMMSS.csv   - For Excel/Tableau
# metrics_YYYYMMDD_HHMMSS.json        - Computed metrics
# paper_tables_YYYYMMDD_HHMMSS.tex    # Ready-to-paste LaTeX tables
```

---

## 📝 Writing Order (Recommended)

| Order | Section | Source | Est. Time |
|-------|---------|--------|-----------|
| 1 | **Methodology (Sec III)** | Your codebase | 2-3 hrs |
| 2 | **Experimental Setup (Sec IV)** | This guide | 30 min |
| 3 | **Run Experiments** | Benchmark script | 5 min |
| 4 | **Results (Sec V)** | Generated data | 1-2 hrs |
| 5 | **Related Work (Sec II)** | Outline + refs.bib | 1-2 hrs |
| 6 | **Discussion (Sec VI)** | Results + limitations | 1-2 hrs |
| 7 | **Introduction (Sec I)** | Frame contributions | 1 hr |
| 8 | **Conclusion (Sec VII)** | Synthesize | 30 min |
| 9 | **Abstract** | Write last | 15 min |

---

## 🔑 Key Numbers to Extract (from benchmark)

| Table | Metric | Source |
|-------|--------|--------|
| V | Accuracy, Macro-F1, Pathogenic Recall, VUS Rate, Cohen's κ | `metrics.json` |
| VI | Per-class P/R/F1 (5 classes) | `metrics.confusion_matrix` |
| VII | Ablation study (run variants) | Additional runs needed |
| VIII | Latency breakdown (ms) | `results.latency_ms` |

### Ablation Study (run separately):
```bash
# Disable DNA scoring - modify main.py to return 0.0
# Disable Protein scoring - modify main.py  
# Disable ClinVar - comment out clinvar_service call
# Disable ACMG - return VUS directly
# Run each and record metrics
```

---

## 📊 Paper Figures to Generate

| Fig | Description | Code |
|-----|-------------|------|
| 1 | System Architecture Pipeline | Draw.io / TikZ |
| 2 | Genomic→CDS Mapping Flowchart | Algorithm 1 |
| 3 | ACMG Bayesian Decision Tree | Algorithm 4 |
| 4 | Confusion Matrix Heatmap | `generate_paper_figures()` |
| 5 | VUS Reclassification Sankey | `generate_paper_figures()` |
| 6 | Ablation Bar Chart | Manual from Table VII |
| 7 | Reliability Diagram (ECE) | `generate_paper_figures()` |

### Generate Figures:
```python
# After benchmark, run:
from benchmark_runner import generate_paper_figures
generate_paper_figures(results, metrics, "benchmark_results/")
```

---

## ✍️ Writing Tips (IEEE Style)

### Do:
- Use passive voice: "The variant **was classified** as..."
- Define acronyms at first use: "ACMG/AMP (American College of Medical Genetics and Genomics/Association for Molecular Pathology)"
- Number equations: `\begin{equation} P(Path|E) = ... \end{equation}`
- Reference figures: "Fig. 1 shows..." not "The figure below shows..."
- Cite references: `\cite{richards2015standards}` → [1]

### Gene/Protein Nomenclature:
- Gene: *BRCA1*, *TP53* (italic)
- Protein: BRCA1, p53 (roman)
- Variants: c.100A>G, p.Arg34His (HGVS)

### Required IEEE Elements:
- [ ] Two-column format (`IEEEtran` class)
- [ ] Figure captions **below** figures
- [ ] Table captions **above** tables  
- [ ] References in `[1]`, `[2]` format (not author-year)
- [ ] 10-12 pages max (conference) / no limit (journal)
- [ ] Index Terms (keywords) after abstract

---

## 📋 Checklist Before Submission

### Content
- [ ] All 5 contributions clearly stated in Introduction
- [ ] Methodology reproducible (algorithms + parameters)
- [ ] Benchmark variants listed (Table IV)
- [ ] Baselines properly cited and configured
- [ ] Statistical significance reported (if applicable)
- [ ] Limitations honestly discussed
- [ ] Ethical statement (clinical use disclaimer)

### Format
- [ ] Compiles without errors (`pdflatex` → `bibtex` → `pdflatex` ×2)
- [ ] All figures 300+ DPI, vector (PDF) preferred
- [ ] Tables fit in one column or span both properly
- [ ] Reference count 40-60
- [ ] No "et al." in bibliography (use full author lists per IEEE)
- [ ] Supplementary material referenced (if any)

### Reproducibility
- [ ] Code available (GitHub link in paper)
- [ ] Benchmark variants in supplementary table
- [ ] Docker/requirements.txt for environment
- [ ] Random seeds reported

---

## 🎯 Target Venues & Deadlines (2024-2025)

| Venue | Type | Page Limit | Deadline* | Fit |
|-------|------|------------|-----------|-----|
| **IEEE JBHI** | Journal | No limit | Rolling | ⭐⭐⭐ Best fit |
| **IEEE/ACM TCBB** | Journal | No limit | Rolling | ⭐⭐⭐ |
| **AMIA Annual** | Conference | 6 pages | ~Mar | ⭐⭐ Clinical focus |
| **ISMB/ECCB** | Conference | 8 pages | ~Jan | ⭐⭐ Bioinformatics |
| **Bioinformatics** | Journal | No limit | Rolling | ⭐⭐ Methods |
| **Genetics in Medicine** | Journal | No limit | Rolling | ⭐ Clinical |

*Check websites for exact dates

---

## 🔧 Customization for Your Paper

### Update These in LaTeX Template:
```latex
% Title
\title{Your Final Title}

% Authors
\author{
  \IEEEauthorblockN{First Last\IEEEauthorrefmark{1}}
  \IEEEauthorblockA{Dept, Univ, City, Country\\ email@domain.com}
}

% Add your ORCID IDs
% \thanks{ORCID: 0000-0000-0000-0000}
```

### Update These in Benchmark:
- Add your benchmark variants to `BENCHMARK_VARIANTS` in `benchmark_runner.py`
- Modify baselines in `run_ablation_study()` function
- Adjust latency measurement if using different hardware

---

## 📞 Support

### Common Issues:
| Issue | Fix |
|-------|-----|
| Backend timeout | Increase `timeout` in `ClinXClient` |
| CUDA OOM on Colab | Reduce window size in `main.py` |
| Import errors | `pip install -r requirements.txt` in virtual env |
| LaTeX compile fail | Check `references.bib` for missing fields |

### Need Help?
- Check `sample_research_paper.pdf` for IEEE structure example
- Review `IEEE_PAPER_OUTLINE.md` for detailed content guidance
- Run `python run_benchmark.py --list-variants` to verify test set

---

**Next Step**: Start backend, run `python run_benchmark.py --quick` to verify pipeline works, then begin writing Methodology section using `IEEE_PAPER_OUTLINE.md` as your guide.

Good luck! 🧬📄