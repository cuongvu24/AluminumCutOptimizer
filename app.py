...
        st.subheader("📊 Mô Phỏng Cắt Từng Thanh")
        selected_profile = st.selectbox("Chọn Mã Thanh", patterns_df['Mã Thanh'].unique())
        filtered = patterns_df[patterns_df['Mã Thanh'] == selected_profile]

        container = st.container()
        with container:
            for idx, row in filtered.iterrows():
                if idx >= 3:
                    with st.expander(f"🔹 #{row['Số Thanh']} | {selected_profile} | {int(row['Chiều Dài Thanh'])}mm"):
                        display_pattern(row, cutting_gap)
                else:
                    st.markdown(f"**🔹 #{row['Số Thanh']} | {selected_profile} | {int(row['Chiều Dài Thanh'])}mm**")
                    display_pattern(row, cutting_gap)

        output = io.BytesIO()
        create_output_excel(output, result_df, patterns_df, summary_df, stock_length, cutting_gap)
        output.seek(0)
        st.download_button("📥 Tải Xuống File Kết Quả Cắt Nhôm", output, "ket_qua_cat_nhom.xlsx")


def display_pattern(row, cutting_gap):
    pattern = row['Mẫu Cắt']
    parts = pattern.split('+')
    current_pos = 0
    fig = go.Figure()

    for i, part in enumerate(parts):
        length = float(part)
        color = f"rgba({(i*40)%255}, {(i*70)%255}, {(i*90)%255}, 0.7)" if i > 0 else "rgba(255, 100, 100, 0.9)"
        fig.add_shape(type="rect", x0=current_pos, x1=current_pos + length, y0=0, y1=1,
                      line=dict(width=1), fillcolor=color)
        fig.add_annotation(x=current_pos + length/2, y=0.5, text=str(int(length)), showarrow=False, font=dict(size=10, color="white"))
        current_pos += length + cutting_gap

    fig.update_layout(
        height=100,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Chiều Dài (mm)", range=[0, row['Chiều Dài Thanh']]),
        yaxis=dict(visible=False),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plot_{row['Số Thanh']}")

# Footer
st.markdown("---")
st.markdown("Phần Mềm Tối Ưu Cắt Nhôm © 2025 By Cường Vũ")
st.markdown("Mọi thắc mắc xin liên hệ Zalo 0977 487 639")
