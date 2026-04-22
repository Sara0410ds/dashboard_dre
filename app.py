def gerar_pdf(df_pivot, fig_comp):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
    import tempfile

    styles = getSampleStyleSheet()
    pdf_file = "dashboard.pdf"

    doc = SimpleDocTemplate(pdf_file)
    elementos = []

    elementos.append(Paragraph("Relatório DRE", styles["Title"]))
    elementos.append(Spacer(1, 12))

    total = df_pivot["Realizado"].sum()
    elementos.append(Paragraph(f"Total Realizado: R$ {total:,.2f}", styles["Normal"]))
    elementos.append(Spacer(1, 12))

    # 🔥 GERA IMAGEM SEM write_image
    img_bytes = fig_comp.to_image(format="png")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        with open(tmp.name, "wb") as f:
            f.write(img_bytes)

        elementos.append(Image(tmp.name, width=500, height=300))

    elementos.append(Spacer(1, 12))

    for _, row in df_pivot.iterrows():
        linha = f"{row['Mes_Nome']} | Dif: {row['Diferença']:.2f} | {row['Status']}"
        elementos.append(Paragraph(linha, styles["Normal"]))

    doc.build(elementos)

    return pdf_file
