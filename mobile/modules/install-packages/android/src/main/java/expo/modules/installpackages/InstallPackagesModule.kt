package expo.modules.installpackages

import android.os.Build
import expo.modules.kotlin.exception.Exceptions
import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class InstallPackagesModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("InstallPackages")

    Function("canRequestPackageInstalls") {
      val context = appContext.reactContext ?: throw Exceptions.ReactContextLost()
      if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
        true
      } else {
        context.packageManager.canRequestPackageInstalls()
      }
    }
  }
}
