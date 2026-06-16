/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define ADC_BUFFER_SIZE 2
#define FILTER_SIZE 8        // 이동평균 필터 크기
#define ADC_MAX_VALUE 4095   // 12bit ADC 최대값
#define DEADZONE_THRESHOLD 20  // 중앙 데드존 임계값 (%)
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc1;
DMA_HandleTypeDef hdma_adc1;

TIM_HandleTypeDef htim2;

UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */
uint16_t adc_buffer[ADC_BUFFER_SIZE];  // DMA 버퍼
uint16_t joystick_x_raw = 0;           // 조이스틱 X축 원시값
uint16_t joystick_y_raw = 0;           // 조이스틱 Y축 원시값
// 이동평균 필터를 위한 배열
uint32_t x_filter_buffer[FILTER_SIZE] = {0};
uint32_t y_filter_buffer[FILTER_SIZE] = {0};
uint8_t filter_index = 0;

// 필터링된 값
uint16_t joystick_x_filtered = 0;
uint16_t joystick_y_filtered = 0;

// 백분율로 변환된 값 (-100 ~ +100)
int16_t joystick_x_percent = 0;
int16_t joystick_y_percent = 0;

// 방향 문자
char direction_char = 'X';
char prev_direction_char = 'X';

char uart_buffer[100];
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_ADC1_Init(void);
static void MX_TIM2_Init(void);
/* USER CODE BEGIN PFP */
void process_joystick_data(void);
uint16_t apply_moving_average_filter(uint16_t new_value, uint32_t *filter_buffer);
int16_t convert_to_percentage(uint16_t adc_value);
char get_direction_char(int16_t x_percent, int16_t y_percent);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
#ifdef __GNUC__
/* With GCC, small printf (option LD Linker->Libraries->Small printf
   set to 'Yes') calls __io_putchar() */
#define PUTCHAR_PROTOTYPE int __io_putchar(int ch)
#else
#define PUTCHAR_PROTOTYPE int fputc(int ch, FILE *f)
#endif /* __GNUC__ */

/**
  * @brief  Retargets the C library printf function to the USART.
  * @param  None
  * @retval None
  */
PUTCHAR_PROTOTYPE
{
  /* Place your implementation of fputc here */
  /* e.g. write a character to the USART1 and Loop until the end of transmission */
  if (ch == '\n')
    HAL_UART_Transmit (&huart2, (uint8_t*) "\r", 1, 0xFFFF);
  HAL_UART_Transmit (&huart2, (uint8_t*) &ch, 1, 0xFFFF);

  return ch;
}

///**
//  * @brief  이동평균 필터 적용
//  * @param  new_value: 새로운 ADC 값
//  * @param  filter_buffer: 필터 버퍼 포인터
//  * @retval 필터링된 값
//  */
//uint16_t apply_moving_average_filter(uint16_t new_value, uint32_t *filter_buffer)
//{
//    static uint8_t x_init = 0, y_init = 0;
//    uint32_t sum = 0;
//
//    // 필터 버퍼 구분 (X축 또는 Y축)
//    if (filter_buffer == x_filter_buffer) {
//        if (!x_init) {
//            // 초기화: 모든 버퍼를 첫 번째 값으로 채움
//            for (int i = 0; i < FILTER_SIZE; i++) {
//                filter_buffer[i] = new_value;
//            }
//            x_init = 1;
//            return new_value;
//        }
//    } else {
//        if (!y_init) {
//            // 초기화: 모든 버퍼를 첫 번째 값으로 채움
//            for (int i = 0; i < FILTER_SIZE; i++) {
//                filter_buffer[i] = new_value;
//            }
//            y_init = 1;
//            return new_value;
//        }
//    }
//
//    // 새로운 값을 버퍼에 추가
//    filter_buffer[filter_index] = new_value;
//
//    // 평균 계산
//    for (int i = 0; i < FILTER_SIZE; i++) {
//        sum += filter_buffer[i];
//    }
//
//    return (uint16_t)(sum / FILTER_SIZE);
//}
//
///**
//  * @brief  ADC 값을 백분율로 변환 (-100 ~ +100)
//  * @param  adc_value: ADC 값 (0 ~ 4095)
//  * @retval 백분율 값
//  */
////int16_t convert_to_percentage(uint16_t adc_value)
////{
////    // ADC 중앙값을 기준으로 -100 ~ +100으로 변환
////    int16_t centered_value = (int16_t)adc_value - (ADC_MAX_VALUE / 2);
////    int16_t percentage = (centered_value * 100) / (ADC_MAX_VALUE / 2);
////
////    // 범위 제한
////    if (percentage > 100) percentage = 100;
////    if (percentage < -100) percentage = -100;
////
////    return percentage;
////}
//
////#define JOY_MIN 600   // 조이스틱을 한쪽 끝으로 밀었을 때 나오는 최소값 (직접 확인 필요)
////#define JOY_MAX 3500  // 조이스틱을 반대쪽 끝으로 밀었을 때 나오는 최대값
////#define JOY_CENTER 2048 // 조이스틱 중앙값
////
////int16_t convert_to_percentage(uint16_t adc_value)
////{
////    int32_t result;
////
////    // 중앙값보다 클 때
////    if (adc_value > JOY_CENTER) {
////        result = ((int32_t)(adc_value - JOY_CENTER) * 100) / (JOY_MAX - JOY_CENTER);
////    }
////    // 중앙값보다 작을 때
////    else {
////        result = ((int32_t)(adc_value - JOY_CENTER) * 100) / (JOY_CENTER - JOY_MIN);
////    }
////
////    // 범위 제한
////    if (result > 100) result = 100;
////    if (result < -100) result = -100;
////
////    return (int16_t)result;
////}
//
////#define RAW_MIN 200    // 실제 조이스틱 최소값
////#define RAW_MAX 3800   // 실제 조이스틱 최대값
////#define RAW_CENTER 2048 // 실제 조이스틱 중앙값
////
////int16_t convert_to_percentage(uint16_t adc_value)
////{
////    int32_t percentage;
////
////    if (adc_value >= RAW_CENTER) {
////        // 중앙값 이상일 때: 0% ~ 100%
////        percentage = ((int32_t)(adc_value - RAW_CENTER) * 100) / (RAW_MAX - RAW_CENTER);
////    } else {
////        // 중앙값 미만일 때: 0% ~ -100%
////        percentage = ((int32_t)(adc_value - RAW_CENTER) * 100) / (RAW_CENTER - RAW_MIN);
////    }
////
////    if (percentage > 100) percentage = 100;
////    if (percentage < -100) percentage = -100;
////
////    return (int16_t)percentage;
////}
//
//// [수정된 설정값]
//// 중앙값은 2048, 4090에 도달하는 순간을 100%로 잡습니다.
//#define RAW_CENTER 2048
//#define RAW_MAX_EFFECTIVE 4090 // 절반만 밀어도 이미 4090이 나오는 지점
//#define RAW_MIN_EFFECTIVE 5    // 반대쪽 끝값 (확인해보고 수정하세요)
//
//int16_t convert_to_percentage(uint16_t adc_value)
//{
//    int32_t percentage;
//
//    // 4090을 넘어가면 강제로 100%로 고정 (클램핑)
//    if (adc_value > RAW_MAX_EFFECTIVE) adc_value = RAW_MAX_EFFECTIVE;
//    if (adc_value < RAW_MIN_EFFECTIVE) adc_value = RAW_MIN_EFFECTIVE;
//
//    if (adc_value >= RAW_CENTER) {
//        // 2048 ~ 4090 구간을 0 ~ 100%로 매핑
//        percentage = ((int32_t)(adc_value - RAW_CENTER) * 100) / (RAW_MAX_EFFECTIVE - RAW_CENTER);
//    } else {
//        // 반대쪽 구간 매핑
//        percentage = ((int32_t)(adc_value - RAW_CENTER) * 100) / (RAW_CENTER - RAW_MIN_EFFECTIVE);
//    }
//
//    return (int16_t)percentage;
//}
//
///**
//  * @brief  조이스틱 데이터 처리
//  * @param  None
//  * @retval None
//  */
//void process_joystick_data(void)
//{
//    // 원시 ADC 값 읽기
//    joystick_x_raw = adc_buffer[0];  // ADC Channel 0 (PA0)
//    joystick_y_raw = adc_buffer[1];  // ADC Channel 1 (PA1)
//
//    // 이동평균 필터 적용
//    joystick_x_filtered = apply_moving_average_filter(joystick_x_raw, x_filter_buffer);
//    joystick_y_filtered = apply_moving_average_filter(joystick_y_raw, y_filter_buffer);
//
//    // 필터 인덱스 업데이트 (두 축 공통 사용)
//    filter_index = (filter_index + 1) % FILTER_SIZE;
//
//    // 백분율로 변환
//    joystick_x_percent = convert_to_percentage(joystick_x_filtered);
//    joystick_y_percent = convert_to_percentage(joystick_y_filtered);
//}
//
///**
//  * @brief  타이머 콜백 함수 (주기적 ADC 읽기용)
//  * @param  htim: 타이머 핸들
//  * @retval None
//  */
//void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
//{
//    if (htim->Instance == TIM2) {
//        // 조이스틱 데이터 처리
//        process_joystick_data();
//
//        // UART로 데이터 출력 (디버깅용)
//        printf("X: %d%% (%d), Y: %d%% (%d)\n",
//                joystick_x_percent, joystick_x_filtered,
//                joystick_y_percent, joystick_y_filtered);
//    }
//}


////////wsad//////////////////////////////////////////////////////////////////////////////////////////////////////


uint16_t apply_moving_average_filter(uint16_t new_value, uint32_t *filter_buffer)
{
    static uint8_t x_init = 0, y_init = 0;
    uint32_t sum = 0;

    if (filter_buffer == x_filter_buffer) {
        if (!x_init) {
            for (int i = 0; i < FILTER_SIZE; i++) {
                filter_buffer[i] = new_value;
            }
            x_init = 1;
            return new_value;
        }
    } else {
        if (!y_init) {
            for (int i = 0; i < FILTER_SIZE; i++) {
                filter_buffer[i] = new_value;
            }
            y_init = 1;
            return new_value;
        }
    }

    filter_buffer[filter_index] = new_value;

    for (int i = 0; i < FILTER_SIZE; i++) {
        sum += filter_buffer[i];
    }

    return (uint16_t)(sum / FILTER_SIZE);
}

int16_t convert_to_percentage(uint16_t adc_value)
{
    int16_t centered_value = (int16_t)adc_value - (ADC_MAX_VALUE / 2);
    int16_t percentage = (centered_value * 100) / (ADC_MAX_VALUE / 2);

    if (percentage > 100) percentage = 100;
    if (percentage < -100) percentage = -100;

    return percentage;
}

/**
  * @brief  조이스틱 위치에 따른 방향 문자 반환
  * @param  x_percent: X축 백분율 (-100 ~ +100), 좌(-) / 우(+)
  * @param  y_percent: Y축 백분율 (-100 ~ +100), 후(-) / 전(+)
  * @retval 방향 문자 (W/A/S/D/X)
  */
char get_direction_char(int16_t x_percent, int16_t y_percent)
{
    int16_t abs_x = (x_percent >= 0) ? x_percent : -x_percent;
    int16_t abs_y = (y_percent >= 0) ? y_percent : -y_percent;

    // 데드존 내부 = 중앙 (X)
    if (abs_x < DEADZONE_THRESHOLD && abs_y < DEADZONE_THRESHOLD) {
        return 'X';
    }

    // Y축이 더 크면 전진/후진 우선
    if (abs_y >= abs_x) {
        if (y_percent >= DEADZONE_THRESHOLD) {
            return 'W';  // 전진
        } else if (y_percent <= -DEADZONE_THRESHOLD) {
            return 'S';  // 후진
        }
    }

    // X축이 더 크면 좌회전/우회전
    if (abs_x > abs_y) {
        if (x_percent >= DEADZONE_THRESHOLD) {
            return 'D';  // 우회전
        } else if (x_percent <= -DEADZONE_THRESHOLD) {
            return 'A';  // 좌회전
        }
    }

    return 'X';  // 기본값: 중앙
}

void process_joystick_data(void)
{
    joystick_x_raw = adc_buffer[0];
    joystick_y_raw = adc_buffer[1];

    joystick_x_filtered = apply_moving_average_filter(joystick_x_raw, x_filter_buffer);
    joystick_y_filtered = apply_moving_average_filter(joystick_y_raw, y_filter_buffer);

    filter_index = (filter_index + 1) % FILTER_SIZE;

    joystick_x_percent = convert_to_percentage(joystick_x_filtered);
    joystick_y_percent = convert_to_percentage(joystick_y_filtered);

    // 방향 문자 결정
    direction_char = get_direction_char(joystick_x_percent, joystick_y_percent);
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM2) {
        process_joystick_data();

        // 방향이 변경되었을 때만 출력 (또는 항상 출력하려면 조건 제거)
        if (direction_char != prev_direction_char) {
            printf("%c\n", direction_char);
            prev_direction_char = direction_char;
        }

        // 디버깅용: 항상 상세 정보 출력 (필요시 주석 해제)
        // printf("Dir: %c | X: %d%%, Y: %d%%\n",
        //        direction_char, joystick_x_percent, joystick_y_percent);
    }
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_USART2_UART_Init();
  MX_ADC1_Init();
  MX_TIM2_Init();
  /* USER CODE BEGIN 2 */
  if (HAL_DMA_Init(&hdma_adc1) != HAL_OK) {
        Error_Handler();
    }

    // ADC1 핸들과 DMA 링크
    __HAL_LINKDMA(&hadc1, DMA_Handle, hdma_adc1);

    // ADC 캘리브레이션
  //  HAL_ADCEx_Calibration_Start(&hadc1);

    // DMA를 사용한 연속 ADC 변환 시작
    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buffer, ADC_BUFFER_SIZE);

    // 타이머 시작 (50ms 주기로 데이터 처리)
    HAL_TIM_Base_Start_IT(&htim2);

    // 시작 메시지
    printf("STM32F103 조이스틱 ADC 읽기 시작\n");
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	  HAL_Delay(10);  // 메인 루프 딜레이
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 16;
  RCC_OscInitStruct.PLL.PLLN = 336;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief ADC1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_ADC1_Init(void)
{

  /* USER CODE BEGIN ADC1_Init 0 */

  /* USER CODE END ADC1_Init 0 */

  ADC_ChannelConfTypeDef sConfig = {0};

  /* USER CODE BEGIN ADC1_Init 1 */

  /* USER CODE END ADC1_Init 1 */

  /** Configure the global features of the ADC (Clock, Resolution, Data Alignment and number of conversion)
  */
  hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
  hadc1.Init.Resolution = ADC_RESOLUTION_12B;
  hadc1.Init.ScanConvMode = ENABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 2;
  hadc1.Init.DMAContinuousRequests = ENABLE;
  hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
  */
  sConfig.Channel = ADC_CHANNEL_0;
  sConfig.Rank = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_480CYCLES;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
  */
  sConfig.Channel = ADC_CHANNEL_1;
  sConfig.Rank = 2;
  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN ADC1_Init 2 */

  /* USER CODE END ADC1_Init 2 */

}

/**
  * @brief TIM2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_TIM2_Init(void)
{

  /* USER CODE BEGIN TIM2_Init 0 */

  /* USER CODE END TIM2_Init 0 */

  TIM_ClockConfigTypeDef sClockSourceConfig = {0};
  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM2_Init 1 */

  /* USER CODE END TIM2_Init 1 */
  htim2.Instance = TIM2;
  htim2.Init.Prescaler = 8399;
  htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim2.Init.Period = 499;
  htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim2) != HAL_OK)
  {
    Error_Handler();
  }
  sClockSourceConfig.ClockSource = TIM_CLOCKSOURCE_INTERNAL;
  if (HAL_TIM_ConfigClockSource(&htim2, &sClockSourceConfig) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim2, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM2_Init 2 */

  /* USER CODE END TIM2_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA2_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA2_Stream0_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA2_Stream0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA2_Stream0_IRQn);

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : LD2_Pin */
  GPIO_InitStruct.Pin = LD2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
