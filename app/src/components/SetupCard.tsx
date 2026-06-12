import React from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

const CARD_MARGIN = 20
const CIRCLE_SIZE = 140
const CIRCLE_COLOR = 'rgba(163, 73, 164, 0.18)'
const ICON_SIZE = 72
const ICON_FILL = '#000000'

export { ICON_SIZE, ICON_FILL }

interface SetupCardProps {
  icon: React.ReactElement
  children: React.ReactNode
  footer: React.ReactNode
  scrollable?: boolean
  testID?: string
}

const SetupCard: React.FC<SetupCardProps> = ({ icon, children, footer, scrollable = false, testID }) => {
  const cardContent = (
    <>
      <View style={styles.iconContainer}>
        <View style={styles.iconCircle}>{icon}</View>
      </View>
      {children}
    </>
  )

  return (
    <SafeAreaView style={styles.safeArea} edges={['left', 'right', 'bottom']} testID={testID}>
      <View style={styles.cardWrapper}>
        <View style={styles.card}>
          {scrollable ? (
            <ScrollView
              contentContainerStyle={styles.cardContent}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              {cardContent}
            </ScrollView>
          ) : (
            <ScrollView
              contentContainerStyle={[styles.cardContent, { flexGrow: 1, justifyContent: 'center' }]}
              showsVerticalScrollIndicator={false}
            >
              {cardContent}
            </ScrollView>
          )}
        </View>
      </View>
      <View style={styles.footer}>
        <View style={styles.buttonInner}>{footer}</View>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  cardWrapper: {
    flex: 1,
    paddingHorizontal: CARD_MARGIN,
    paddingTop: 28,
    paddingBottom: 16,
  },
  card: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(170,170,170,0.4)',
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 4,
  },
  cardContent: {
    padding: 28,
  },
  iconContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  iconCircle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: CIRCLE_COLOR,
    alignItems: 'center',
    justifyContent: 'center',
  },
  footer: {
    alignItems: 'center',
    paddingTop: 20,
    paddingBottom: 16,
  },
  buttonInner: {
    width: '42%',
    minWidth: 148,
  },
})

export default SetupCard
