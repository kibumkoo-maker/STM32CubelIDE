# Rotary_Encoder_TIM


## NUCLEO-F103RB 기준 하드웨어 구성:
* Encoder A Phase (CH1): PA6 (TIM3_CH1) ← D12
* Encoder B Phase (CH2): PA7 (TIM3_CH2) ← D11
* USART2 (디버그 출력): PA2(TX), PA3(RX) — 115200 baud
* B1 버튼: PC13 — Encoder count 리셋
* LD2: PA5 — 동작 표시 LED





## 📁 프로젝트 구조
```
C:\work\stm32_rotary_encoder\
└── Core\
    ├── Inc\main.h
    └── Src\main.c
```
## 🔌 하드웨어 연결 (NUCLEO-F103RB)
| 신호    | 핀    | TIM3 매핑    | 보드 커넥터 |
|:------:|:------:|:------:|:------:|
| Encoder Phase A    | PA6    | TIM3_CH1    | D12 |
| Encoder Phase B    | PA7    | TIM3_CH2    | D11 |
| USART2 TX    | PA2    | -    | - |
| USART2 RX    | PA3    | -    | - |
| B1 (Reset)    | PC13    | -    | User Button |
| LD2 (LED)    | PA5    | -    | Built-in LED |

## ⚙️ TIM3 Encoder Mode 동작 원리
 *타이머를 Encoder Mode TI1+TI2 (SMS=011) 로 설정하여 하드웨어적으로 로터리 엔코더의 위상차를 감지합니다:
```   
PA6 (TI1)  ──┬──┬──┬──┬──    ↑    ↑         ↑    ↑
             │  │  │  │      TI1  TI2       TI1  TI2
PA7 (TI2)  ──┬──┬──┬──┬──    rising rising   rising  rising
             │  │  │  │      + low  + low    + high  + high
         CW: └──┘──┘──┘──▶  COUNT UP        COUNT DOWN
         CCW: ◀──┘──┘──┘──  COUNT DOWN       COUNT UP
```
* 4배 분해능: A/B 두 신호의 모든 엣지에서 카운트 (기계식 24PPR → 96 counts/회전)
* 자동 방향 감지: TIM3->CR1 레지스터의 DIR 비트가 하드웨어에서 자동 갱신
* 오버플로우 자연 처리: int16_t 차분 연산으로 16-bit 타이머 랩어라운드에 강건
## 🧠 주요 코드 설명
1.타이머 초기화 (MX_TIM3_Encoder_Init)
 *레지스터 직접 설정 방식으로 HAL 의존성 없이 동작:
```
TIM3->SMCR = (0x03 << 0);       // Encoder Mode 3 (TI1+TI2)
TIM3->CCMR1 = (0x01 << 0) |     // CC1S=01: TI1 selected
              (0x01 << 8);       // CC2S=01: TI2 selected
TIM3->PSC = 0;                   // 프리스케일러 없음 (최대 해상도)
TIM3->ARR = 0xFFFF;              // 16-bit 풀 레인지
```
2. 위치 추적 (PrintEncoderStatus)
* 16-bit 타이머 카운터의 차분을 누적하여 32-bit 위치 값으로 확장:
```
int16_t diff = (int16_t)(TIM3->CNT) - g_last_count;
g_encoder_pos += diff;           // 오버플로우에 강건한 누적
```
3. 버튼 리셋 (HAL_GPIO_EXTI_Callback)
* B1 버튼(PC13) Rising Edge 인터럽트 → 메인루프에서 카운터 리셋 + LED 3번 점멸
```  
📟 USART 출력 예시
========================================
  Rotary Encoder Demo (TIM3 Encoder Mode)
========================================
  POS: position  CNT: timer  DIR: direction
----------------------------------------
POS:     +0  CNT:     0  DIR: CW (+)
POS:    +12  CNT:    12  DIR: CW (+)
POS:    +24  CNT:    24  DIR: CW (+)
POS:    +22  CNT:    22  DIR: CCW (-)
>>> ENCODER RESET (B1 pressed) <<<
POS:     +0  CNT:     0  DIR: CW (+)
```
```c
/* USER CODE BEGIN Includes */
#include <stdio.h>
/* USER CODE END Includes */
```
```c
/* USER CODE BEGIN PD */
/* Timer period for 16-bit encoder counter (max value) */
#define ENCODER_TIM_PERIOD        0xFFFF

/* Minimum position change before printing to USART */
#define PRINT_THRESHOLD           1
/* USER CODE END PD */
```
```c
/* USER CODE BEGIN PV */
/* Encoder position tracking */
static volatile int32_t  g_encoder_pos   = 0;    /* Cumulative encoder position */
static          int16_t  g_last_count    = 0;    /* Previous TIM3 counter value */

/* Button flag - set in EXTI callback, cleared in main loop */
static volatile uint8_t  g_btn_reset     = 0;

/* User LED on/off flag for activity indication */
static          uint8_t  g_led_active    = 0;
/* USER CODE END PV */
```
```c
/* USER CODE BEGIN PFP */
static void MX_TIM3_Encoder_Init(void);
static void PrintEncoderStatus(void);
/* USER CODE END PFP */
```
```c
/* USER CODE BEGIN 0 */

/**
  * --------------------------------------------------------------------------
  * @brief  TIM3 Encoder Mode Initialization (Register-level)
  *
  * Configures TIM3 in Encoder Mode TI1+TI2 using register-level access.
  * This avoids dependency on CubeMX-generated HAL_TIM_Encoder_MspInit(),
  * making the code self-contained and regeneration-safe.
  *
  * @note   TIM3_CH1 = PA6 (Encoder Phase A)
  *         TIM3_CH2 = PA7 (Encoder Phase B)
  *
  * Encoder Mode TI1+TI2 (SMS=011):
  *   - Counter counts on every edge of both TI1 and TI2 signals
  *   - 4x resolution compared to a single pulse per detent
  *   - Direction bit (CR1:DIR) updates automatically based on phase relationship
  *
  *   TI1 rising  + TI2 low  => count UP
  *   TI1 rising  + TI2 high => count DOWN
  *   TI2 rising  + TI1 low  => count DOWN
  *   TI2 rising  + TI1 high => count UP
  * --------------------------------------------------------------------------
  */
static void MX_TIM3_Encoder_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* ---- Enable peripheral clocks ---- */
    __HAL_RCC_TIM3_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /* ---- Configure GPIO for encoder inputs ---- */
    /* PA6 (TIM3_CH1) and PA7 (TIM3_CH2) as floating inputs.
     * Timer peripheral reads the pin state directly from GPIO input.
     * Use GPIO_PULLUP if encoder has open-collector outputs.
     * Use GPIO_NOPULL if encoder has push-pull outputs (recommended). */
    GPIO_InitStruct.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* ---- Reset TIM3 to default state ---- */
    __HAL_RCC_TIM3_FORCE_RESET();
    __HAL_RCC_TIM3_RELEASE_RESET();

    /* ---- TIM3 basic configuration ---- */
    TIM3->PSC = 0;                       /* No prescaler (count at APB1 timer clock) */
    TIM3->ARR = ENCODER_TIM_PERIOD;      /* Auto-reload at 0xFFFF (max 16-bit range) */

    /* ---- Slave mode: Encoder mode 3 (TI1+TI2) ---- */
    /* SMS[2:0] = 011  =>  Encoder mode: count on both edges of TI1 and TI2 */
    TIM3->SMCR = (0x03 << 0);

    /* ---- Capture/Compare Mode Register 1 ---- */
    /* CC1S[1:0] = 01  =>  TI1 selected on channel 1 (PA6 input) */
    /* CC2S[1:0] = 01  =>  TI2 selected on channel 2 (PA7 input) */
    /* IC1F[3:0] = 0000 => No input capture filter */
    /* IC2F[3:0] = 0000 => No input capture filter */
    /* IC1PSC[1:0] = 00  => No input prescaler */
    /* IC2PSC[1:0] = 00  => No input prescaler */
    TIM3->CCMR1 = (0x01 << 0) |   /* CC1S = 01 */
                  (0x01 << 8);    /* CC2S = 01 */

    /* ---- Capture/Compare Enable Register ---- */
    /* CC1P = 0, CC2P = 0  => Rising edge active (no polarity inversion) */
    /* CC1E = 1, CC2E = 1  => Enable capture on channels 1 and 2 */
    TIM3->CCER &= ~(TIM_CCER_CC1P | TIM_CCER_CC2P);
    TIM3->CCER |=  (TIM_CCER_CC1E | TIM_CCER_CC2E);

    /* ---- Generate update event to reload registers ---- */
    TIM3->EGR |= TIM_EGR_UG;

    /* ---- Enable counter ---- */
    TIM3->CR1 |= TIM_CR1_CEN;
}


/**
  * --------------------------------------------------------------------------
  * @brief  Print encoder status to USART2
  *
  * Reads the current TIM3 counter, computes the difference from the last
  * read, and updates the cumulative position. Uses 16-bit signed arithmetic
  * to naturally handle timer overflow/underflow:
  *
  *   Example overflow:  65530 -> 5   =>  5 - (-6)   = +11  (CW)
  *   Example underflow: 5     -> 65530 => -6 - 5    = -11  (CCW)
  *
  * Output format:  "POS:  +1234  CNT:  5678  DIR: CW (+)"
  * --------------------------------------------------------------------------
  */
static void PrintEncoderStatus(void)
{
    /* Read current timer count as signed 16-bit for overflow-safe diff */
    int16_t current_cnt  = (int16_t)(TIM3->CNT & 0xFFFF);
    int16_t diff         = current_cnt - g_last_count;

    if (diff == 0)
    {
        return;                         /* No change since last read */
    }

    /* Update cumulative position */
    g_encoder_pos += diff;
    g_last_count   = current_cnt;

    /* Toggle LED for activity feedback */
    if (diff > 0)
    {
        HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_SET);
    }
    else
    {
        HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);
    }

    /* Format and transmit via USART2 */
    char buf[64];
    int len = snprintf(buf, sizeof(buf),
        "POS: %+6ld  CNT: %5d  DIR: %s\r\n",
        (long)g_encoder_pos,
        current_cnt,
        (diff > 0) ? "CW (+)" : "CCW (-)");

    HAL_UART_Transmit(&huart2, (uint8_t*)buf, (uint16_t)len, 100);
}


/**
  * --------------------------------------------------------------------------
  * @brief  EXTI line callback (B1 button press)
  *
  * Called from HAL_GPIO_EXTI_IRQHandler when B1 (PC13) rising edge is detected.
  * Sets a flag that is processed in the main loop to reset the encoder counter.
  * --------------------------------------------------------------------------
  */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == B1_Pin)
    {
        g_btn_reset = 1;
    }
}

/* USER CODE END 0 */
```
```c
    /* USER CODE BEGIN 2 */

    /* Initialize TIM3 in encoder mode */
    MX_TIM3_Encoder_Init();

    /* Capture initial counter value */
    g_last_count = (int16_t)(TIM3->CNT & 0xFFFF);

    /* Set LED on to indicate system running */
    HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_SET);
    g_led_active = 1;

    /* Startup message */
    char start_msg[] =
        "\r\n"
        "========================================\r\n"
        "  Rotary Encoder Demo (TIM3 Encoder Mode)\r\n"
        "========================================\r\n"
        "  Encoder: TIM3_CH1 (PA6) + TIM3_CH2 (PA7)\r\n"
        "  Mode:    TI1+TI2 (4x resolution)\r\n"
        "  Button:  B1 (PC13) = Reset counter\r\n"
        "  LED:     LD2 (PA5) = CW=ON, CCW=OFF\r\n"
        "----------------------------------------\r\n"
        "  POS: position  CNT: timer  DIR: direction\r\n"
        "----------------------------------------\r\n"
        "\r\n";
    HAL_UART_Transmit(&huart2, (uint8_t*)start_msg, sizeof(start_msg) - 1, 100);

    /* USER CODE END 2 */
```
```c
    /* USER CODE BEGIN WHILE */
    while (1)
    {
        /* ---- Encoder position update and display ---- */
        PrintEncoderStatus();

        /* ---- Button reset handling ---- */
        if (g_btn_reset)
        {
            g_btn_reset = 0;

            /* Reset timer counter and position tracking */
            TIM3->CNT = 0;
            g_last_count = 0;
            g_encoder_pos = 0;

            /* Visual confirmation: 3 quick blinks */
            for (int i = 0; i < 3; i++)
            {
                HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);
                HAL_Delay(80);
                HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_SET);
                HAL_Delay(80);
            }

            char reset_msg[] = ">>> ENCODER RESET (B1 pressed) <<<\r\n\r\n";
            HAL_UART_Transmit(&huart2, (uint8_t*)reset_msg, sizeof(reset_msg) - 1, 100);
        }

        /* Throttle loop to prevent USART flooding (~200 Hz update rate) */
        HAL_Delay(5);

        /* USER CODE END WHILE */
```
*정방향


*역방향
