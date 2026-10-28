# Graphical Settings

### Disable PostFX

[Link To Original Post](https://discord.com/channels/1099468797410283540/1150655466830041128)

```
{
    "FFlagDisablePostFx": true
}
```

### Change Rendering Mode

[Link To Original Post](https://discord.com/channels/1099468797410283540/1173220043266457660)

For D3D11 (DirectX 11):

```
{
    "FFlagDebugGraphicsPreferD3D11": true
}
```

For D3D11FL10 (DirectX 11 but with the feature list of DirectX 10):

```
{
    "FFlagDebugGraphicsPreferD3D11FL10": true
}
```

For Vulkan:

**Caution**

Performance may vary (Worse on nvidia cards). Expect visual bugs and crashes.

```
{
    "FFlagDebugGraphicsPreferVulkan": true
}
```

For OpenGL:

```
{
    "FFlagDebugGraphicsPreferOpenGL": true
}
```

For Metal:

**Important**

Only for MacOS.

```
{
    "FFlagDebugGraphicsPreferMetal": true
}
```

### Better Light Attenuation

**Warning**

May cause lighting artifacts.\


[Link To Original Post](https://discord.com/channels/1099468797410283540/1165003069814226964)

```
{
    "FFlagNewLightAttenuation": true
}
```

### Disable Baked Shadows

[Link To Original Post](https://discord.com/channels/1099468797410283540/1173308420133232750)

```
{
    "DFFlagDebugPauseVoxelizer": true
}
```

### Force LOD For All Meshes

[Link To Original Post](https://discord.com/channels/1099468797410283540/1146963091775553536)

```
{
    "DFIntCSGLevelOfDetailSwitchingDistance":0,
    "DFIntCSGLevelOfDetailSwitchingDistanceL12":0,
    "DFIntCSGLevelOfDetailSwitchingDistanceL23":0,
    "DFIntCSGLevelOfDetailSwitchingDistanceL34":0
}
```

### Remove Player Clothing Textures

[Link To Original Post](https://discord.com/channels/1099468797410283540/1207722310195486720)

```
{
    "DFIntTextureCompositorActiveJobs": 0
}
```

### Skip MipMaps

**Note**

Set to anything below 0 to basically delete all textures.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1247944649822441634)

```
{
  "FIntDebugTextureManagerSkipMips": 0
}
```

### Force Texture Quality

**Note**

Set to any value from 0 to 3.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1150312397274357871)

```
{
    "DFFlagTextureQualityOverrideEnabled": true,
    "DFIntTextureQualityOverride": 3
}
```

### Uncap FPS

[Link To Original Post](https://discord.com/channels/1099468797410283540/1245740082841780224)

```
{
    "DFIntTaskSchedulerTargetFps": 9999,
    "FFlagTaskSchedulerLimitTargetFpsTo2402": false
}
```

### FRM Quality Level Override

**Note**

Forces graphics quality. Render distance will still incerase however. Values range from 1 - 10 and 1 - 21 if using 21 bars.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1184157587562823780)

```
{
    "DFIntDebugFRMQualityLevelOverride": 1
}
```

### Enable MSAA

**Caution**

Values over 4 will cause viewports (3D Models) to be invisible.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1145231575173316608)

```
{
    "FIntDebugForceMSAASamples": 0
}
```

### Low Poly Terrain

[Link To Original Post](https://discord.com/channels/1099468797410283540/1194889014981967932)

```
{
    "FIntTerrainArraySliceSize": 8
}
```

### Remove Player Shadows

[Link To Original Post](https://discord.com/channels/1099468797410283540/1147409993302282240)

```
{
    "FIntRenderShadowIntensity": 0
}
```

### ShadowMap Bias

[Link To Original Post](https://discord.com/channels/1099468797410283540/1152409274933317712)

```
{
    "FIntRenderShadowmapBias": 75
}
```

# UI/UX (User Interface)

### Rename Charts Tab Back To Discover

[Link To Original Post](https://discord.com/channels/1099468797410283540/1254997424116863048)

```
{
    "FFlagLuaAppChartsPageRenameIXP": false
}
```

### Rainbow UI / Viewport

[Link To Original Post](https://discord.com/channels/1099468797410283540/1183833667945103421)

```
{
    "FFlagDebugDisplayUnthemedInstances": true
}
```

### Position Update UI/UX

[Link To Original Post](https://discord.com/channels/1099468797410283540/1267153647033384980)

```
{
    "FFlagAccessoryAdjustmentEnabled2":true,
    "FFlagHumanoidDescriptionUseInstances5":true,
    "FFlagHumanoidDescriptionFallback":true,
    "FFlagEnableNonUAPAccessoryAdjustment":true,
    "FFlagAXAccessoryAdjustment": true,
    "FFlagAXAccessoryAdjustmentIXPEnabled": true,
    "FFlagAXAccessoryAdjustmentIXPEnabledForAll": true,
    "FFlagAXAvatarFetchResultCamelCase": true,
    "FFlagAccessoryAdjustmentEnabled3": true
}
```

### Chrome FTUX (First Time User Experience)

[Link To Original Post](https://discord.com/channels/1099468797410283540/1271975274719875104)

```
{
    "FFlagDebugEnableVRFTUXExperienceInStudio": true,
    "FFlagEnableChromeFTUX": true,
    "FFlagEnableVRFTUXExperienceV2": true
}
```

### Revert To Old Report Menu

[Link To Original Post](https://discord.com/channels/1099468797410283540/1204420123260092436)

```
{
    "FFlagEnableReportAbuseMenuRoactABTest2": false,
    "FFlagEnableReportAbuseMenuRoact2": false,
    "FFlagEnableReportAbuseMenuLayerOnV3": false
}
```

### Disable Beta Badge

[Link To Original Post](https://discord.com/channels/1099468797410283540/1194581451857997844)

```
{
    "FFlagVoiceBetaBadge": false,
    "FFlagTopBarUseNewBadge": false,
    "FFlagEnableBetaBadgeLearnMore": false,
    "FFlagBetaBadgeLearnMoreLinkFormview": false,
    "FFlagControlBetaBadgeWithGuac": false,
    "FStringVoiceBetaBadgeLearnMoreLink": ""
}
```

### Disable Chat Translation

[Link To Original Post](https://discord.com/channels/1099468797410283540/1204335548160938025)

```
{
    "FFlagChatTranslationSettingEnabled3": false
}
```

### Fix Beta Badge Dupe

[Link To Original Post](https://discord.com/channels/1099468797410283540/1194581451857997844)

```
{
    "FFlagFixDupeBetaBadge": true
}
```

### Disable Haptics Toggle

[Link To Original Post](https://discord.com/channels/1099468797410283540/1268891182302494772)

```
{
    "FFlagAddHapticsToggle": false
}
```

### Disable Self View

[Link To original Post](https://discord.com/channels/1099468797410283540/1183081644614226012)

```
{
    "FFlagCoreGuiTypeSelfViewPresent": false
}
```

### Chat Keylogger

[Link To Original Post](https://discord.com/channels/1099468797410283540/1193962531128102955)

```
{
    "FFlagDebugTextBoxServiceShowOverlay": true
}
```

### Remove Home Button

[Link To Original Post](https://discord.com/channels/1099468797410283540/1171224254352732201)

```
{
    "FFlagInGameMenuHomeButton": false
}
```

### Chrome Pin Chat

[Link To Original Post](https://discord.com/channels/1099468797410283540/1177942263100362792)

```
{
    "FFlagEnableChromePinnedChat": true
}
```

### Hide GUI

**Note**

Set to a id of a group you are in.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1149975417818722314)

```
{
    "DFIntCanHideGuiGroupId": 0
}
```

### Set Custom Font Size

[Link To Original Post](https://discord.com/channels/1099468797410283540/1170204803025088512)

```
{
    "FIntFontSizePadding": 1
}
```

### Cleaner ESC Settings Menu

[Link To Original Post](https://discord.com/channels/1099468797410283540/1189607691849564230)

```
{
    "FFlagEnableAudioOutputDevice": false,
    "FIntV1MenuLanguageSelectionFeaturePerMillageRollout": 0,
    "FFlagChatTranslationSettingEnabled3": false
}
```

### Disable "Output device" UI from Escape Menu

[Link To Original Post](https://discord.com/channels/1099468797410283540/1184771500558012416)

```
{
    "FFlagEnableAudioOutputDevice": false
}
```

### Disable Fullscreen Titlebar

[Link To Original Post](https://discord.com/channels/1099468797410283540/1198606462226792468)

```
{
    "FIntFullscreenTitleBarTriggerDelayMillis": 3600000
}
```

### Chrome UI

**Caution**

May cause the game to not load in certain games.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1156809517883985960)

```
{
    "FFlagEnableInGameMenuChrome": true
}
```

# QOL (Quality Of Life)

### Disable VR Collision Fade

[Link To Original Post](https://discord.com/channels/1099468797410283540/1258459675314360493)

```
{
  "FFlagViewCollisionFadeToBlackInVR": "False"
}
```

### Disable AD Portals

[Link To Original Post](https://discord.com/channels/1099468797410283540/1179502701118230529)

```
{
    "FFlagAdServiceEnabled": false
}
```

### Scroll Speed

[Link To Original Post](https://discord.com/channels/1099468797410283540/1142226024281690132)

```
{
    "FIntScrollWheelDeltaAmount": 0
}
```

### Disable Telemetry

**Note**

Does not disable all telemetry.

[Link To Original Post](https://discord.com/channels/1099468797410283540/1155133604389728396)

```
{
    "FFlagDebugDisableTelemetryEphemeralCounter": true,
	"FFlagDebugDisableTelemetryEphemeralStat": true,
	"FFlagDebugDisableTelemetryEventIngest": true,
	"FFlagDebugDisableTelemetryPoint": true,
	"FFlagDebugDisableTelemetryV2Counter": true,
	"FFlagDebugDisableTelemetryV2Event": true,
	"FFlagDebugDisableTelemetryV2Stat": true
}
```

# Voice Chat

### Voice Chat Volume

[Link To Original Post](https://discord.com/channels/1099468797410283540/1208100665138745424)

**Note**

Default value is 1000 (in thousandths).

```
{
    "DFIntVoiceChatVolumeThousandths": 1000
}
```

### Return Old Voice Chat Bubble [WARNING: DISABLES AVATAR CHAT]

[Link To Original Post](https://discord.com/channels/1099468797410283540/1139960093132210227)

```
{
    "DFFlagFacialAnimationStreaming2": false
}
```

# Misc

### Enable New Camera Mode

[Link To Original Post](https://discord.com/channels/1099468797410283540/1237065400315805789)

```
{
    "FFlagNewCameraControls": true
}
```

### Enable Audio Occlusion

[Link To Original Post](https://discord.com/channels/1099468797410283540/1239510612577620039)

```
{
    "FFlagDebugEnableDirectAudioOcclusion2": true
}
```

### Make Your Flags Work On Certain Games Only

[Link To Original Post](https://discord.com/channels/1099468797410283540/1239329199404355584)

### Sky's Flag Collection

[Link To Original Post](https://discord.com/channels/1099468797410283540/1139962301991104582)

### Surfing The Web Inside of Roblox

[Link To Original Post](https://discord.com/channels/1099468797410283540/1165211319583117443)

```
{
    "FFlagTopBarUseNewBadge": true,
    "FStringTopBarBadgeLearnMoreLink": "https://example.com",
    "FStringVoiceBetaBadgeLearnMoreLink": "https://example.com"
}
```

### Notes

> Roblox was supposed to kill fastflags like 6 months ago. Now here I am updating this collection again. Roblox really trolled me with this one.

## About

*No description, website, or topics provided.*

### Resources

[Readme](https://github.com/CfwSky/fastflags-collection#readme-ov-file)

[Activity](https://github.com/CfwSky/fastflags-collection/activity)

### Stars

**27** stars

### Watchers

**2** watching

### Forks

[**4**](https://github.com/CfwSky/fastflags-collection/forks)[ forks](https://github.com/CfwSky/fastflags-collection/forks)

[Report repository](https://github.com/contact/report-content?content_url=https%3A%2F%2Fgithub.com%2FCfwSky%2Ffastflags-collection\&report=CfwSky+%28user%29)