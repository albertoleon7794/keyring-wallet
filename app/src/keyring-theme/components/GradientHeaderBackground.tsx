import React from 'react'
import { StyleProp, ViewStyle } from 'react-native'
import LinearGradient from 'react-native-linear-gradient'

interface GradientHeaderBackgroundProps {
  style?: StyleProp<ViewStyle>
}

const GRADIENT_COLORS = ['#2E4953', '#622C62', '#6E121D']
const GRADIENT_LOCATIONS = [0.00962, 0.50962, 1]

const GradientHeaderBackground: React.FC<GradientHeaderBackgroundProps> = ({ style }) => (
  <LinearGradient
    colors={GRADIENT_COLORS}
    locations={GRADIENT_LOCATIONS}
    start={{ x: 0, y: 0 }}
    end={{ x: 1, y: 0 }}
    style={[{ flex: 1 }, style]}
  />
)

export default GradientHeaderBackground
