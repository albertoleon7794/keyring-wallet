export enum RemoteLoggerEventTypes {
  ENABLE_REMOTE_LOGGING = 'RemoteLogging.Enable',
}

export class RemoteLogger {
  create() {
    return this
  }
  log() {}
  info() {}
  warn() {}
  error() {}
  debug() {}
  trace() {}
  test() {}
}
