# Bug 修复审查报告

## Bug 1（图片字段）：✅ 有条件通过

- 接口定义 `image_url: string`，模板使用 `dish.image_url || '/placeholder.png'`
- 代码内部一致，默认占位图处理合理
- **限制**：无法独立验证后端 API 是否实际返回 `image_url` 字段，需对照后端接口文档或实际抓包确认。如果后端返回字段名不符，图片仍将显示为占位图。

---

## Bug 2（按钮状态）：⚠️ 有条件通过（需小修）

- `actionLoading` ref 声明 ✓
- "接单"按钮：`type="success" :disabled="actionLoading"` ✓
- "取消订单"按钮：`type="danger" :disabled="actionLoading"` ✓
- API 调用前设置 `actionLoading = true`，finally 中重置 ✓
- 刷新后 `expandedRows` 通过 filter 保留展开状态 ✓

**问题**：`confirmed` 状态下的"结账"按钮（`type="warning"`）**缺失** `:disabled="actionLoading"`：

```vue
<el-button
  v-if="row.status === 'confirmed'"
  type="warning"
  @click.stop="handleStatusUpdate(row, 'paid')"
>
  结账
</el-button>
```

连续点击"结账"仍可发起多次 API 请求，建议补充 `:disabled="actionLoading"`。

---

## Bug 3（二维码）：✅ 通过

- `qrCodeUrl` ref 声明 ✓
- `generateQRCode()` 使用 `qrcode` 库生成 DataURL，异步加载无性能阻塞 ✓
- 二维码内容格式：`${orderData.id}:${orderData.total_amount}:${Date.now()}` 包含订单号+金额+时间戳，格式合理 ✓
- 错误处理完善：try/catch 捕获生成失败，仅 console.error，不影响页面其他功能 ✓
- 模板中 `<img v-if="qrCodeUrl" :src="qrCodeUrl">` 配合 fallback 显示支付码文字，体验良好 ✓

---

## 综合结论

| Bug | 结论 | 说明 |
|-----|------|------|
| Bug 1 | 有条件通过 | API 字段名需人工确认 |
| Bug 2 | 有条件通过 | 结账按钮缺 actionLoading 禁用 |
| Bug 3 | 通过 | 无问题 |

**建议操作：**
1. 对照后端 API 确认菜品接口返回字段名为 `image_url`
2. 为"结账"按钮补充 `:disabled="actionLoading"`
3. 两项小修完成后可标记为完全通过
