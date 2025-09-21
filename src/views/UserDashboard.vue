<template>
  <div class="dashboard-container">
    <div class="charts-row">
      <div class="chart-wrapper">
        <div ref="genderChart" class="chart"></div>
        <div class="chart-title">性别比例分布</div>
      </div>
      <div class="chart-wrapper">
        <div ref="ageChart" class="chart"></div>
        <div class="chart-title">年龄分布</div>
      </div>
    </div>
    <div class="charts-row">
      <div class="chart-wrapper">
        <div ref="provinceChart" class="chart"></div>
        <div class="chart-title">各省人口分布</div>
      </div>
      <div class="chart-wrapper">
        <div ref="surnameChart" class="chart"></div>
        <div class="chart-title">姓氏分布</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { API_CONFIG } from '@/config/config';

const genderChart = ref(null)
const ageChart = ref(null)
const provinceChart = ref(null)
const surnameChart = ref(null)
let genderChartInstance = null
let ageChartInstance = null
let provinceChartInstance = null
let surnameChartInstance = null

// 渲染性别比例分布图表
const renderGenderChart = async () => {
  try {
    // 向后端请求性别分布数据
    const response = await axios.get(`${API_CONFIG.BASE_URL}/bigdata/gender-distribution`)
    const data = response.data
    const total = data.male_count + data.female_count

    genderChartInstance = echarts.init(genderChart.value)

    const option = {
      title: {
        text: `总人数: ${total}`,
        left: '5%',
        top: '5%',
        textStyle: {
          fontSize: 14,
          fontWeight: 'normal',
          color: '#666'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: params => {
          return `${params.name}: ${params.value}人 (${params.percent}%)`
        }
      },
      series: [
        {
          name: '性别分布',
          type: 'pie',
          radius: '70%',
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: '{b}: {d}%',
            position: 'outside'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '14',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true,
            length: 10,
            length2: 15
          },
          data: [
            {
              value: data.male_count,
              name: '男',
              itemStyle: {
                color: '#1890ff',
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
              }
            },
            {
              value: data.female_count,
              name: '女',
              itemStyle: {
                color: '#f04864',
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
              }
            }
          ]
        }
      ]
    }

    genderChartInstance.setOption(option)

  } catch (error) {
    console.error('获取性别分布数据失败:', error)
  }
}

// 渲染年龄分布图表
const renderAgeChart = async () => {
  try {
    const response = await axios.get(`${API_CONFIG.BASE_URL}/bigdata/age-distribution`);
    const data = response.data;

    ageChartInstance = echarts.init(ageChart.value);

    const option = {
      title: {
        name: '年龄分布',
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function(params) {
          const maleCount = params[0].data;
          const femaleCount = params[1].data;
          const total = maleCount + femaleCount;
          return `
            ${params[0].name}<br/>
            男: ${maleCount}人<br/>
            女: ${femaleCount}人<br/>
            总数: ${total}人
          `;
        }
      },
      legend: {
        data: ['男', '女'],
        top: 30
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: data.age_groups,
        axisLabel: {
          interval: 0,
          rotate: 30
        }
      },
      yAxis: {
        type: 'value',
        name: '人数'
      },
      series: [
        {
          name: '男',
          type: 'bar',
          stack: 'gender',  // 使用相同的stack名称实现堆叠
          data: data.male_counts,
          itemStyle: {
            color: '#1890ff',
            borderColor: '#fff',
            borderWidth: 1
          }
        },
        {
          name: '女',
          type: 'bar',
          stack: 'gender',  // 使用相同的stack名称实现堆叠
          data: data.female_counts,
          itemStyle: {
            color: '#f04864',
            borderColor: '#fff',
            borderWidth: 1
          }
        }
      ]
    };

    ageChartInstance.setOption(option);

  } catch (error) {
    console.error('获取年龄分布数据失败:', error);
  }
};

// 渲染各省人口分布图表
const renderProvinceChart = async () => {
  try {
    const response = await axios.get(`${API_CONFIG.BASE_URL}/bigdata/province-distribution`);
    const data = response.data;

    provinceChartInstance = echarts.init(provinceChart.value);

    // 为每个省设置不同的颜色
    const colors = [
      '#1890ff', '#f04864', '#52c41a', '#ffc107', '#2f54eb', '#fa541c',
      '#722ed1', '#13c2c2', '#3f8600', '#ff9800', '#8c52ff', '#096dd9',
      '#ff3860', '#1877f2', '#2fc25b', '#ff7800', '#702179', '#00b96b',
      '#ffd430', '#223273', '#ff6767', '#00c292', '#3466d8', '#ff8542',
      '#854dff', '#00a9e5', '#ff4d4f', '#22c55e', '#007aff', '#ff9900'
    ];

    const provinceData = data.province_counts;
    const provinces = Object.keys(provinceData);
    const seriesData = provinces.map((province, index) => ({
      value: provinceData[province],
      name: province,
      itemStyle: {
        color: colors[index % colors.length],
        shadowBlur: 10,
        shadowColor: 'rgba(0, 0, 0, 0.3)'
      }
    }));

    const option = {
      title: {
        text: `总人数: ${data.total}`,
        left: '5%',
        top: '5%',
        textStyle: {
          fontSize: 14,
          fontWeight: 'normal',
          color: '#666'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: params => {
          return `${params.name}: ${params.value}人 (${params.percent}%)`;
        }
      },
      series: [
        {
          name: '各省人口分布',
          type: 'pie',
          radius: '70%',
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: '{b}: {d}%',
            position: 'outside'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '14',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true,
            length: 10,
            length2: 15
          },
          data: seriesData
        }
      ]
    };

    provinceChartInstance.setOption(option);

  } catch (error) {
    console.error('获取各省人口分布数据失败:', error);
  }
};

// 渲染姓氏分布图表
const renderSurnameChart = async () => {
  try {
    const response = await axios.get(`${API_CONFIG.BASE_URL}/bigdata/firstname-distribution`);
    const data = response.data;

    surnameChartInstance = echarts.init(surnameChart.value);

    // 为每个姓氏设置不同的颜色
    const colors = [
      '#1890ff', '#f04864', '#52c41a', '#ffc107', '#2f54eb', '#fa541c',
      '#722ed1', '#13c2c2', '#3f8600', '#ff9800', '#8c52ff', '#096dd9',
      '#ff3860', '#1877f2', '#2fc25b', '#ff7800', '#702179', '#00b96b',
      '#ffd430', '#223273', '#ff6767', '#00c292', '#3466d8', '#ff8542',
      '#854dff', '#00a9e5', '#ff4d4f', '#22c55e', '#007aff', '#ff9900'
    ];

    const surnameData = data.first_names;
    const surnames = Object.keys(surnameData);
    const seriesData = surnames.map((surname, index) => ({
      value: surnameData[surname],
      name: surname,
      itemStyle: {
        color: colors[index % colors.length],
        shadowBlur: 10,
        shadowColor: 'rgba(0, 0, 0, 0.3)'
      }
    }));

    const option = {
      title: {
        text: `总人数: ${data.total}`,
        left: '5%',
        top: '5%',
        textStyle: {
          fontSize: 14,
          fontWeight: 'normal',
          color: '#666'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: params => {
          return `${params.name}: ${params.value}人 (${params.percent}%)`;
        }
      },
      series: [
        {
          name: '姓氏分布',
          type: 'pie',
          radius: '70%',
          center: ['50%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: '{b}: {d}%',
            position: 'outside'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '14',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true,
            length: 10,
            length2: 15
          },
          data: seriesData
        }
      ]
    };

    surnameChartInstance.setOption(option);

  } catch (error) {
    console.error('获取姓氏分布数据失败:', error);
  }
};

// 处理窗口 resize 事件
const handleResize = () => {
  if (genderChartInstance) genderChartInstance.resize()
  if (ageChartInstance) ageChartInstance.resize()
  if (provinceChartInstance) provinceChartInstance.resize()
  if (surnameChartInstance) surnameChartInstance.resize()
}

// 组件挂载时的生命周期钩子函数
onMounted(() => {
  renderGenderChart()
  renderAgeChart()
  renderProvinceChart()
  renderSurnameChart()
  window.addEventListener('resize', handleResize)
})

// 组件卸载时的生命周期钩子函数
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (genderChartInstance) {
    genderChartInstance.dispose()
    genderChartInstance = null
  }
  if (ageChartInstance) {
    ageChartInstance.dispose()
    ageChartInstance = null
  }
  if (provinceChartInstance) {
    provinceChartInstance.dispose()
    provinceChartInstance = null
  }
  if (surnameChartInstance) {
    surnameChartInstance.dispose()
    surnameChartInstance = null
  }
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.charts-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 20px;
}

.chart-wrapper {
  flex: 1;
  min-width: 300px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 15px;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  position: relative;
}

.chart-wrapper:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.2);
}

.chart {
  width: 100%;
  height: 300px;
}

.chart-title {
  text-align: center;
  margin-top: 10px;
  font-size: 16px;
  font-weight: bold;
  color: '#333';
}

@media (max-width: 768px) {
 .charts-row {
    flex-direction: column;
  }
}
</style>