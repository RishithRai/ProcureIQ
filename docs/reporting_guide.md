# Executive briefing builder

1. Choose the exact reporting scope. Source compatibility is checked when previewing and downloading.
2. Select spending insights, review recommendations, compatible saved cases/analyst findings and an explicitly calculated financial scenario. Only cases from the shell's current namespace can be included. Search covers the loaded first 100 cases; exact-ID input is a secondary fallback.
3. Preview the generated five-slide content. Use the slide buttons to inspect each slide, then Download Presentation. Evidence JSON and compatible scenario Excel are secondary downloads.

The preview is dynamic content/layout extracted from the generated editable PPTX, not pixel-exact Office rendering. Download requests pin its content hash; a changed finding or source requires another preview. Original PPTX/XLSX generators and compatibility rules remain authoritative. Included analyst findings are attributed, with frozen citations in evidence JSON and editable presentation speaker notes. Hypothetical scenario outputs are never described as realized savings.

See [full workflow](product_workflow_refinement.md) and [executed verification](product_workflow_verification.md).
