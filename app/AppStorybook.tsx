// import { initLanguages } from '@bifold/core'
import React from 'react'
import { LogBox } from 'react-native'

// import keyring from './src'
import StorybookUIRoot from './storybook'

// const { localization } = keyring

// initLanguages(localization)

LogBox.ignoreAllLogs()

const Base = () => {
  return <StorybookUIRoot />
}

export default Base
