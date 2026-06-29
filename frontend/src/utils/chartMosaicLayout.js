/** 6 图 Bento 错落布局：宽/高/列跨度不一致，填满可视区域 */
export const defaultMosaicLayout = [
  { colSpan: 7, rowSpan: 2, size: 'lg' },
  { colSpan: 5, rowSpan: 1, size: 'md' },
  { colSpan: 5, rowSpan: 1, size: 'md' },
  { colSpan: 4, rowSpan: 1, size: 'sm' },
  { colSpan: 4, rowSpan: 1, size: 'sm' },
  { colSpan: 4, rowSpan: 1, size: 'sm' }
]

export function buildMosaicCharts(chartDefs, buildOption) {
  return defaultMosaicLayout.map((layout, index) => ({
    title: chartDefs[index]?.title ?? `Chart ${index + 1}`,
    ...layout,
    option: buildOption(index, chartDefs[index])
  }))
}
