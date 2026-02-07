<template>
  <div class="offline-modal-overlay">
    <div class="offline-modal">
      <div class="offline-icon">⚠️</div>
      <h2 class="offline-title">Service Offline</h2>
      <p class="offline-message">Unable to connect to the backend service</p>
      
      <!-- Circular countdown timer -->
      <div class="countdown-container">
        <svg class="countdown-svg" viewBox="0 0 100 100">
          <circle
            class="countdown-circle-bg"
            cx="50"
            cy="50"
            r="45"
          />
          <circle
            class="countdown-circle"
            cx="50"
            cy="50"
            r="45"
            :style="circleStyle"
          />
        </svg>
        <div class="countdown-text">{{ remainingSeconds }}</div>
      </div>
      
      <p class="retry-message">Retrying connection in {{ remainingSeconds }} seconds...</p>
      
      <button @click="retryNow" class="btn-retry">
        Retry Now
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['retry']);

const totalSeconds = 15;
const remainingSeconds = ref(totalSeconds);
let countdownInterval = null;

// Calculate circle dash offset for animation
const circleStyle = computed(() => {
  const circumference = 2 * Math.PI * 45; // radius = 45
  const progress = remainingSeconds.value / totalSeconds;
  const offset = circumference * (1 - progress);
  
  return {
    strokeDasharray: `${circumference} ${circumference}`,
    strokeDashoffset: offset,
    transition: 'stroke-dashoffset 1s linear'
  };
});

const startCountdown = () => {
  // Clear any existing countdown
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }
  
  // Reset to full countdown
  remainingSeconds.value = totalSeconds;
  
  countdownInterval = setInterval(() => {
    remainingSeconds.value--;
    
    if (remainingSeconds.value <= 0) {
      clearInterval(countdownInterval);
      countdownInterval = null;
      emit('retry');
      // The retry will check backend; if still offline, countdown will restart
    }
  }, 1000);
};

const retryNow = () => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
  emit('retry');
  // The retry will check backend; if still offline, countdown will restart
};

// Watch for visibility changes to restart countdown
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    startCountdown();
  } else {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
  }
}, { immediate: true });

onMounted(() => {
  if (props.visible) {
    startCountdown();
  }
});

onBeforeUnmount(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
});
</script>

<style scoped>
.offline-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100000;
  backdrop-filter: blur(5px);
  animation: fadeIn 0.3s ease;
}

.offline-modal {
  background: linear-gradient(135deg, #2c2c2c, #1a1a1a);
  border-radius: 16px;
  padding: 2.5rem;
  max-width: 450px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  text-align: center;
  border: 2px solid #ff6b6b;
  animation: slideUp 0.3s ease;
}

.offline-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  animation: pulse 2s ease-in-out infinite;
}

.offline-title {
  color: #ff6b6b;
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  letter-spacing: -0.5px;
}

.offline-message {
  color: #ccc;
  font-size: 1rem;
  margin-bottom: 2rem;
}

.countdown-container {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 1.5rem;
}

.countdown-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.countdown-circle-bg {
  fill: none;
  stroke: #333;
  stroke-width: 8;
}

.countdown-circle {
  fill: none;
  stroke: #ff6b6b;
  stroke-width: 8;
  stroke-linecap: round;
}

.countdown-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 2.5rem;
  font-weight: 700;
  color: #fff;
  font-family: 'Courier New', monospace;
}

.retry-message {
  color: #aaa;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
}

.btn-retry {
  background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.85rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.btn-retry:hover {
  background: linear-gradient(135deg, #ee5a6f, #d43f5a);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.btn-retry:active {
  transform: translateY(0);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}
</style>
