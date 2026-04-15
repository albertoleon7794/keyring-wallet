import BulletPointWithText from '@/components/BulletPointWithText'
import SetupCard, { ICON_SIZE, ICON_FILL } from '@/components/SetupCard'
import { useTheme, testIdWithKey, ThemedText, Button, ButtonType } from '@bifold/core'
import React from 'react'
import { useTranslation } from 'react-i18next'
import { View } from 'react-native'

import PasswordIcon from '../assets/img/setup-password.svg'

export interface PINExplainerProps {
  continueCreatePIN: () => void
}

const strokeProps = {
  stroke: ICON_FILL,
  strokeWidth: 0.8 * (486.8 / ICON_SIZE),
  strokeLinejoin: 'round' as const,
  strokeLinecap: 'round' as const,
}

const PINExplainer: React.FC<PINExplainerProps> = ({ continueCreatePIN }) => {
  const { t } = useTranslation()
  const { Spacing } = useTheme()

  return (
    <SetupCard
      icon={<PasswordIcon width={ICON_SIZE} height={ICON_SIZE} fill={ICON_FILL} {...strokeProps} />}
      footer={
        <Button
          title={t('Global.Continue')}
          accessibilityLabel={t('Global.Continue')}
          testID={testIdWithKey('ContinueCreatePIN')}
          onPress={continueCreatePIN}
          buttonType={ButtonType.Primary}
        />
      }
    >
      <ThemedText style={{ marginBottom: Spacing.md, fontSize: 22, fontWeight: '600', textAlign: 'center' }}>
        {t('PINCreate.Explainer.PrimaryHeading')}
      </ThemedText>
      <View style={{ marginTop: Spacing.sm }}>
        <BulletPointWithText translationKey={'PINCreate.Explainer.Bullet1'} iconColor="#A349A4" />
        <BulletPointWithText translationKey={'PINCreate.Explainer.Bullet2'} iconColor="#A349A4" />
      </View>
    </SetupCard>
  )
}

export default PINExplainer
