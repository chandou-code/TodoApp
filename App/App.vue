<script>
export default {
	onLaunch: function() {
		console.log('App Launch')
		// 添加全局错误处理
		uni.onError((error) => {
			console.error('全局错误:', error)
		})
	},
	onShow: function() {
		console.log('App Show')
	},
	onHide: function() {
		console.log('App Hide')
	}
}
</script>

<style>
	/* 全局样式 */
	page {
		font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
		background-color: #f8f8f8;
		color: #333;
	}
	
	/* 按钮基础样式重置 */
	button {
		line-height: 1.4;
		font-size: 32rpx;
		font-family: inherit;
	}
	
	/* 确保弹窗样式正确 */
	.uni-popup {
		z-index: 9999;
	}
</style>
