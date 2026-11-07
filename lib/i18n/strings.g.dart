// Generated file. Do not edit.
//
// Slang multi-language translations for CommunityFitness (es, en, ca, fr, pt).
// ignore_for_file: unused_element, unused_field, camel_case_types, annotate_overrides, prefer_single_quotes, non_constant_identifier_names, library_private_types_in_public_api

// 🎯 Dart imports:
import 'dart:ui';

// 🐦 Flutter imports:
import 'package:flutter/widgets.dart';

/// Supported locales in CommunityFitness (matching ComuniteApp).
enum AppLocale {
  es(languageCode: 'es', bcp47Code: 'es-ES', nativeName: 'Español'),
  en(languageCode: 'en', bcp47Code: 'en-US', nativeName: 'English'),
  ca(languageCode: 'ca', bcp47Code: 'ca-ES', nativeName: 'Català'),
  fr(languageCode: 'fr', bcp47Code: 'fr-FR', nativeName: 'Français'),
  pt(languageCode: 'pt', bcp47Code: 'pt-PT', nativeName: 'Português');

  const AppLocale({required this.languageCode, required this.bcp47Code, required this.nativeName});

  final String languageCode;
  final String bcp47Code;
  final String nativeName;

  Locale get flutterLocale => Locale(languageCode);

  Translations build() {
    switch (this) {
      case AppLocale.es:
        return _TranslationsEs();
      case AppLocale.en:
        return _TranslationsEn();
      case AppLocale.ca:
        return _TranslationsCa();
      case AppLocale.fr:
        return _TranslationsFr();
      case AppLocale.pt:
        return _TranslationsPt();
    }
  }
}

/// Global translation accessor (`t.common...`, `t.dashboard...`, `t.aiCoach...`).
Translations get t => LocaleSettings.instance.currentTranslations;

class AppLocaleUtils {
  AppLocaleUtils._();

  static List<Locale> get supportedLocales => AppLocale.values.map((l) => l.flutterLocale).toList(growable: false);

  static AppLocale parse(String rawLocale) {
    final normalized = rawLocale.trim().toLowerCase();
    if (normalized.startsWith('es')) return AppLocale.es;
    if (normalized.startsWith('ca')) return AppLocale.ca;
    if (normalized.startsWith('fr')) return AppLocale.fr;
    if (normalized.startsWith('pt')) return AppLocale.pt;
    if (normalized.startsWith('en')) return AppLocale.en;
    return AppLocale.es;
  }
}

class LocaleSettings {
  LocaleSettings._();

  static final LocaleSettings instance = LocaleSettings._();

  static final ValueNotifier<AppLocale> _localeNotifier = ValueNotifier<AppLocale>(AppLocale.en);

  static ValueNotifier<AppLocale> get localeNotifier => _localeNotifier;

  static AppLocale get currentLocale => _localeNotifier.value;

  static Translations _currentTranslations = _localeNotifier.value.build();

  Translations get currentTranslations => _currentTranslations;

  static AppLocale setLocale(AppLocale locale) {
    _currentTranslations = locale.build();
    _localeNotifier.value = locale;
    return locale;
  }

  static AppLocale setLocaleRaw(String rawLocale) {
    final parsed = AppLocaleUtils.parse(rawLocale);
    return setLocale(parsed);
  }

  static AppLocale useDeviceLocale() {
    final deviceLang = PlatformDispatcher.instance.locale.languageCode;
    return setLocaleRaw(deviceLang);
  }
}

class TranslationProvider extends StatefulWidget {
  final Widget child;

  const TranslationProvider({super.key, required this.child});

  static InheritedLocaleData of(BuildContext context) {
    final inherited = context.dependOnInheritedWidgetOfExactType<InheritedLocaleData>();
    if (inherited != null) {
      return inherited;
    }
    return InheritedLocaleData(
      locale: LocaleSettings.currentLocale,
      translations: LocaleSettings.instance.currentTranslations,
      child: const SizedBox.shrink(),
    );
  }

  @override
  State<TranslationProvider> createState() => _TranslationProviderState();
}

class _TranslationProviderState extends State<TranslationProvider> {
  @override
  void initState() {
    super.initState();
    LocaleSettings.localeNotifier.addListener(_onLocaleChanged);
  }

  @override
  void dispose() {
    LocaleSettings.localeNotifier.removeListener(_onLocaleChanged);
    super.dispose();
  }

  void _onLocaleChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    final locale = LocaleSettings.currentLocale;
    return InheritedLocaleData(locale: locale, translations: LocaleSettings.instance.currentTranslations, child: widget.child);
  }
}

class InheritedLocaleData extends InheritedWidget {
  final AppLocale locale;
  final Translations translations;

  const InheritedLocaleData({super.key, required this.locale, required this.translations, required super.child});

  Locale get flutterLocale => locale.flutterLocale;

  @override
  bool updateShouldNotify(covariant InheritedLocaleData oldWidget) {
    return oldWidget.locale != locale;
  }
}

// =============================================================================
// Translations Contract & Per-Locale Implementations (en, es, ca, fr, pt)
// =============================================================================

abstract class Translations {
  _StringsCommon get common;
  _StringsDashboard get dashboard;
  _StringsAiCoach get aiCoach;
  _StringsAnalytics get analytics;
  _StringsWorkout get workout;
  _StringsHybridAi get hybridAi;

  String translateMuscle(String canonicalMuscle) {
    return aiCoach.muscles[canonicalMuscle] ?? canonicalMuscle;
  }

  String translateEquipment(String canonicalEquipment) {
    return aiCoach.equipment[canonicalEquipment] ?? canonicalEquipment;
  }

  String translateConstraint(String canonicalConstraint) {
    return aiCoach.constraints[canonicalConstraint] ?? canonicalConstraint;
  }
}

abstract class _StringsCommon {
  String get appName;
  String get language;
  String get selectLanguage;
  String get cancel;
  String get close;
  Map<String, String> get languages;
}

abstract class _StringsDashboard {
  String get aiCoachTooltip;
  String get dataManagementTooltip;
  String get muscleAnalyticsTooltip;
  String get languageTooltip;
  String get readyToTrain;
  String workoutsThisWeek({required Object count});
  String get freestyleTraining;
  String exercisesPlanned({required Object count});
  String get buildOnTheFly;
  String get totalSets;
  String get movements;
  String get targetIntensity;
  String get startRoutine;
  String get startFreestyle;
  String get exploreAndManage;
  String get routinesTitle;
  String routinesSubtitle({required Object count});
  String get muscleRecoveryTitle;
  String muscleRecoverySubtitle({required Object count});
  String get exerciseCatalogTitle;
  String exerciseCatalogSubtitle({required Object count});
  String get dataMigrationTitle;
  String get dataMigrationSubtitle;
  String get targetMusclesReady;
  String get recentWorkouts;
  String get noWorkoutsYet;
  String get workoutSession;
  String exercisesCount({required Object count});
  String get deleteSessionTooltip;
  String get deleteSessionConfirmTitle;
  String deleteSessionConfirmMessage({required Object title});
  String get deleteSessionConfirmButton;
}

abstract class _StringsAiCoach {
  String get headerTitle;
  String get modelBadge;
  String get liveActive;
  String get liveVoiceToggle;
  String get analyzingMovements;
  String get youLabel;
  String get liveCoachBadge;
  String get flashCoachBadge;
  String get startAiWorkoutNow;
  String setsRepsRest({required Object sets, required Object reps, required Object rest});
  String get form3dBadge;
  String get formDemoBadge;
  String welcomeMessage({required Object chatModel, required Object liveModel});
  _StringsAiCoachLiveBanner get liveBanner;
  _StringsAiCoachContextCard get contextCard;
  _StringsAiCoachPlannerCard get plannerCard;
  _StringsAiCoachAlternativesSheet get alternativesSheet;
  _StringsAiCoachChatInput get chatInput;
  Map<String, String> get muscles;
  Map<String, String> get equipment;
  Map<String, String> get constraints;
  _StringsAiCoachErrors get errors;
}

abstract class _StringsAiCoachLiveBanner {
  String get listeningMic;
  String get connecting;
  String get listening;
  String get thinking;
  String get speaking;
  String get disconnected;
  String get defaultHint;
  String get endSessionTooltip;
  String get quickChipChestAbs;
  String get quickPromptChestAbs;
  String get quickChipBackBiceps;
  String get quickPromptBackBiceps;
  String get quickChipLegsGlutes;
  String get quickPromptLegsGlutes;
}

abstract class _StringsAiCoachContextCard {
  String targetExercise({required Object name});
  String get subtitle;
}

abstract class _StringsAiCoachPlannerCard {
  String get title;
  String get availableEquipment;
  String buildPlanButton({required Object muscles, required Object equipment});
}

abstract class _StringsAiCoachAlternativesSheet {
  String title({required Object name});
  String get customHint;
}

abstract class _StringsAiCoachChatInput {
  String get listeningHint;
  String get liveHint;
  String get defaultHint;
  String get sendTooltip;
  String get stopMicTooltip;
  String get startMicTooltip;
}

abstract class _StringsAiCoachErrors {
  String get loadAlternatives;
  String get buildPlan;
  String get coachReply;
}

abstract class _StringsAnalytics {
  String get screenTitle;
  String get workoutsTitle;
  String get thisWeekSubtitle;
  String get volumeTitle;
  String get bodyMapTitle;
  String get frontViewTab;
  String get backViewTab;
  String get anteriorChainLabel;
  String get posteriorChainLabel;
  String get recoveredStatus;
  String get recoveringStatus;
  String get fatiguedStatus;
  String get zoneUnderMev;
  String get zoneOptimalMav;
  String get zoneNearMrv;
  String get zoneOverMrv;
  String weeklySetsRange({required Object current, required Object min, required Object max});
  String recoveryPercent({required Object percent});
  String exploreMuscleExercises({required Object muscle});
  String get muscleRecoverySectionTitle;
  String readyCountBadge({required Object ready, required Object total});
  String setsMevSummary({required Object sets, required Object mavMax, required Object mev});
  String get estimated1rmSectionTitle;
  String get noPrsYet;
  String bestSetSubtitle({required Object weight, required Object reps});
}

abstract class _StringsWorkout {
  String get finishButton;
  String get durationLabel;
  String get completedSetsLabel;
  String get exercisesLabel;
  String get addExerciseButton;
  String get machineBusySwapPill;
  String get machineBusyModalTitle;
  String ghostPaceCompare({required Object live, required Object target});
  String ghostAheadBadge({required Object delta});
  String ghostBehindBadge({required Object delta});
  String get ghostOnPaceBadge;
  String get anatomicalCardHeader;
  String ghostVerdictAhead({required Object delta});
  String ghostVerdictBehind({required Object delta});
  String get ghostVerdictOnPace;
  String get ghostVerdictCompleted;
  String get muscleActivationSectionTitle;
  String get copyShareCardButton;
  String get doneButton;
  String get cardCopiedSnackbar;
}

abstract class _StringsHybridAi {
  String get aiCoachToggleChip;
  String get routerTitle;
  String npuStatusPrefix({required Object status});
  String get statusOnDeviceReady;
  String get statusDownloadable;
  String get statusDownloading;
  String get statusCloudFallback;
  String get sourceOnDeviceNano;
  String get sourceOnDeviceApple;
  String get sourceOnDeviceChrome;
  String get sourceOnDeviceShort;
  String sourceInCloud({required Object model});
  String get sourceInCloudShort;
  String get sourceOfflineEngine;
  String get ramWarmedUp;
  String get downloadModelButton;
  String dotpromptBadge({required Object templateId});
  String remoteConfigOnlyBadge({required Object templateId});
  String get modeSectionTitle;
  String get modeSectionSubtitle;
  String get modePreferOnDevice;
  String get modeOnlyOnDevice;
  String get modePreferInCloud;
  String get modeOnlyInCloud;
  String get loggerTitle;
  String get loggerSubtitle;
  String get presetHeavyBenchChip;
  String get presetFastSquatChip;
  String get inputHint;
  String get analyzeSetButton;
  String get scanEquipmentButton;
  String get loadLabel;
  String get repsLabel;
  String get rpeLabel;
  String get fatigueAlertBadge;
  String get optimalVelocityBadge;
  String get visionCardTitle;
  String get activeWorkoutSectionTitle;
  String get rpe7Chip;
  String get rpe85Chip;
  String get rpe95Chip;
  String get fatigueAlertBannerBadge;
  String recHighFatigueWithWeight({required Object rpe, required Object weight});
  String recHighFatigueNoWeight({required Object rpe});
  String recNearFailureWithWeight({required Object rpe, required Object weight});
  String recNearFailureNoWeight({required Object rpe});
  String recProgressiveOverload({required Object rpe, required Object weight, required Object reps});
  String recOptimalWithWeight({required Object rpe, required Object weight, required Object reps});
  String recOptimalNoWeight({required Object rpe, required Object reps});
  String errorOnlyOnDeviceUnavailable({required Object status});
}

// -----------------------------------------------------------------------------
// Español (es)
// -----------------------------------------------------------------------------

class _TranslationsEs extends Translations {
  @override
  final _StringsCommon common = _StringsCommonEs();
  @override
  final _StringsDashboard dashboard = _StringsDashboardEs();
  @override
  final _StringsAiCoach aiCoach = _StringsAiCoachEs();
  @override
  final _StringsAnalytics analytics = _StringsAnalyticsEs();
  @override
  final _StringsWorkout workout = _StringsWorkoutEs();
  @override
  final _StringsHybridAi hybridAi = _StringsHybridAiEs();
}

class _StringsCommonEs extends _StringsCommon {
  @override
  String get appName => 'COMMUNITY FITNESS';
  @override
  String get language => 'Idioma';
  @override
  String get selectLanguage => 'Seleccionar Idioma';
  @override
  String get cancel => 'Cancelar';
  @override
  String get close => 'Cerrar';
  @override
  Map<String, String> get languages => const {'es': 'Español', 'en': 'English', 'ca': 'Català', 'fr': 'Français', 'pt': 'Português'};
}

class _StringsDashboardEs extends _StringsDashboard {
  @override
  String get aiCoachTooltip => 'ATLAS • Entrenador Personal IA';
  @override
  String get dataManagementTooltip => 'Gestión de Datos';
  @override
  String get muscleAnalyticsTooltip => 'Analítica Muscular';
  @override
  String get languageTooltip => 'Cambiar Idioma';
  @override
  String get readyToTrain => 'LISTO PARA ENTRENAR';
  @override
  String workoutsThisWeek({required Object count}) => '$count entrenamientos esta semana';
  @override
  String get freestyleTraining => 'Entrenamiento Libre';
  @override
  String exercisesPlanned({required Object count}) => '$count ejercicios planificados';
  @override
  String get buildOnTheFly => 'Crea tu sesión al instante';
  @override
  String get totalSets => 'SERIES TOTALES';
  @override
  String get movements => 'EJERCICIOS';
  @override
  String get targetIntensity => 'INTENSIDAD OBJETIVO';
  @override
  String get startRoutine => 'Iniciar Rutina';
  @override
  String get startFreestyle => 'Entreno Libre';
  @override
  String get exploreAndManage => 'EXPLORAR Y GESTIONAR';
  @override
  String get routinesTitle => 'Rutinas';
  @override
  String routinesSubtitle({required Object count}) => '$count rutinas guardadas';
  @override
  String get muscleRecoveryTitle => 'Recuperación Muscular';
  @override
  String muscleRecoverySubtitle({required Object count}) => '$count músculos listos';
  @override
  String get exerciseCatalogTitle => 'Catálogo de Ejercicios';
  @override
  String exerciseCatalogSubtitle({required Object count}) => '$count movimientos';
  @override
  String get dataMigrationTitle => 'Migración de Datos';
  @override
  String get dataMigrationSubtitle => 'Hevy / Strong / JSON';
  @override
  String get targetMusclesReady => 'MÚSCULOS LISTOS PARA HOY';
  @override
  String get recentWorkouts => 'ENTRENAMIENTOS RECIENTES';
  @override
  String get noWorkoutsYet => 'Aún no hay entrenamientos registrados. ¡Empieza tu primera sesión arriba!';
  @override
  String get workoutSession => 'Sesión de Entrenamiento';
  @override
  String exercisesCount({required Object count}) => '$count ejercicios';
  @override
  String get deleteSessionTooltip => 'Eliminar sesión';
  @override
  String get deleteSessionConfirmTitle => '¿Eliminar entrenamiento?';
  @override
  String deleteSessionConfirmMessage({required Object title}) =>
      'Se eliminará "$title" de tus entrenamientos recientes. Esta acción no se puede deshacer.';
  @override
  String get deleteSessionConfirmButton => 'Eliminar';
}

class _StringsAiCoachEs extends _StringsAiCoach {
  @override
  String get headerTitle => 'ENTRENADOR PERSONAL IA';
  @override
  String get modelBadge => 'ATLAS • Entrenador Biomecánico IA';
  @override
  String get liveActive => 'ATLAS Live Activo';
  @override
  String get liveVoiceToggle => 'Activar ATLAS Live';
  @override
  String get analyzingMovements => 'ATLAS está analizando ejercicios del catálogo...';
  @override
  String get youLabel => 'TÚ';
  @override
  String get liveCoachBadge => 'ATLAS • EN VIVO';
  @override
  String get flashCoachBadge => 'ATLAS • COACH IA';
  @override
  String get startAiWorkoutNow => 'Empezar Este Entrenamiento IA Ahora';
  @override
  String setsRepsRest({required Object sets, required Object reps, required Object rest}) => '$sets series × $reps reps • ${rest}s descanso';
  @override
  String get form3dBadge => 'Forma 3D';
  @override
  String get formDemoBadge => 'Demo';
  @override
  String welcomeMessage({required Object chatModel, required Object liveModel}) =>
      '¡Hola! Soy ATLAS, tu Entrenador Personal IA de CommunityFitness. ¡Selecciona los músculos que quieres entrenar, pregúntame cualquier duda en tu idioma o pide alternativas en casa sin pesas para cualquier ejercicio del catálogo!';
  @override
  final _StringsAiCoachLiveBanner liveBanner = _StringsAiCoachLiveBannerEs();
  @override
  final _StringsAiCoachContextCard contextCard = _StringsAiCoachContextCardEs();
  @override
  final _StringsAiCoachPlannerCard plannerCard = _StringsAiCoachPlannerCardEs();
  @override
  final _StringsAiCoachAlternativesSheet alternativesSheet = _StringsAiCoachAlternativesSheetEs();
  @override
  final _StringsAiCoachChatInput chatInput = _StringsAiCoachChatInputEs();
  @override
  Map<String, String> get muscles => const {
    'Chest': 'Pecho',
    'Back': 'Espalda',
    'Shoulders': 'Hombros',
    'Biceps': 'Bíceps',
    'Triceps': 'Tríceps',
    'Quadriceps': 'Cuádriceps',
    'Quads': 'Cuádriceps',
    'Hamstrings': 'Isquiotibiales',
    'Glutes': 'Glúteos',
    'Calves': 'Gemelos',
    'Abs / Core': 'Abdomen / Core',
    'Core': 'Core',
    'Legs': 'Piernas',
    'Arms': 'Brazos',
    'Full Body': 'Cuerpo Completo',
  };
  @override
  Map<String, String> get equipment => const {
    'All': 'Todo',
    'Home / Bodyweight': 'En Casa / Peso Corporal',
    'Dumbbells Only': 'Solo Mancuernas',
    'Bodyweight': 'Peso Corporal',
    'Barbell': 'Barra',
    'Dumbbell': 'Mancuerna',
    'Machine': 'Máquina',
    'Cable': 'Polea',
    'Kettlebell': 'Pesa Rusa',
  };
  @override
  Map<String, String> get constraints => const {
    'At Home / No Weights': 'En Casa / Sin Pesas',
    'Bodyweight Only': 'Solo Peso Corporal',
    'Dumbbells Only': 'Solo Mancuernas',
    'Joint Friendly': 'Cuidado Articular',
  };
  @override
  final _StringsAiCoachErrors errors = _StringsAiCoachErrorsEs();
}

class _StringsAiCoachLiveBannerEs extends _StringsAiCoachLiveBanner {
  @override
  String get listeningMic => 'ESCUCHANDO TU MICRÓFONO — HABLA CON ATLAS';
  @override
  String get connecting => 'CONECTANDO CON ATLAS EN VIVO...';
  @override
  String get listening => 'ESCUCHANDO • HABLA O USA UN COMANDO DE VOZ';
  @override
  String get thinking => 'PENSANDO • RAZONAMIENTO BIOMECÁNICO EN TIEMPO REAL';
  @override
  String get speaking => 'ATLAS ESTÁ HABLANDO • EN VIVO';
  @override
  String get disconnected => 'DESCONECTADO';
  @override
  String get defaultHint => 'Pide a tu Entrenador Personal en Vivo indicaciones por voz en tiempo real o cambios de ejercicios para casa.';
  @override
  String get endSessionTooltip => 'Finalizar Sesión de Voz en Vivo';
  @override
  String get quickChipChestAbs => 'Pecho y Abdomen en Casa (Sin Pesas)';
  @override
  String get quickPromptChestAbs => 'Dame una rutina de pecho y abdominales en casa sin pesas';
  @override
  String get quickChipBackBiceps => 'Espalda y Bíceps en Casa';
  @override
  String get quickPromptBackBiceps => 'Planifica un entrenamiento de espalda y bíceps en casa';
  @override
  String get quickChipLegsGlutes => 'Piernas y Glúteos Peso Corporal';
  @override
  String get quickPromptLegsGlutes => 'Crea una rutina de piernas y glúteos con peso corporal';
}

class _StringsAiCoachContextCardEs extends _StringsAiCoachContextCard {
  @override
  String targetExercise({required Object name}) => 'EJERCICIO OBJETIVO: $name';
  @override
  String get subtitle => '¿Necesitas una alternativa porque entrenas en casa o te falta material? Toca una opción:';
}

class _StringsAiCoachPlannerCardEs extends _StringsAiCoachPlannerCard {
  @override
  String get title => '¿QUÉ MÚSCULOS QUIERES ENTRENAR HOY?';
  @override
  String get availableEquipment => 'EQUIPAMIENTO DISPONIBLE';
  @override
  String buildPlanButton({required Object muscles, required Object equipment}) => 'Crear Plan de $muscles ($equipment)';
}

class _StringsAiCoachAlternativesSheetEs extends _StringsAiCoachAlternativesSheet {
  @override
  String title({required Object name}) => 'Alternativas IA para $name';
  @override
  String get customHint => 'Nota personalizada (ej. en casa con silla, dolor de muñeca)...';
}

class _StringsAiCoachChatInputEs extends _StringsAiCoachChatInput {
  @override
  String get listeningHint => 'Escuchando tu micrófono... Toca el botón rojo para enviar';
  @override
  String get liveHint => 'Toca el mic para hablar o escribe a ATLAS Live...';
  @override
  String get defaultHint => 'Pide alternativas en casa o toca el mic para hablar...';
  @override
  String get sendTooltip => 'Enviar Mensaje';
  @override
  String get stopMicTooltip => 'Detener Grabación y Enviar Voz';
  @override
  String get startMicTooltip => 'Grabar Voz (16kHz PCM)';
}

class _StringsAiCoachErrorsEs extends _StringsAiCoachErrors {
  @override
  String get loadAlternatives => 'No se pudieron cargar las alternativas en este momento.';
  @override
  String get buildPlan => 'No se pudo crear el plan de entrenamiento en este momento.';
  @override
  String get coachReply => 'El entrenador no pudo responder en este momento.';
}

class _StringsAnalyticsEs extends _StringsAnalytics {
  @override
  String get screenTitle => 'Balance y Recuperación Muscular';
  @override
  String get workoutsTitle => 'Entrenos';
  @override
  String get thisWeekSubtitle => 'Esta semana';
  @override
  String get volumeTitle => 'Volumen';
  @override
  String get bodyMapTitle => 'Mapa Anatómico de Volumen 3D';
  @override
  String get frontViewTab => 'Frontal';
  @override
  String get backViewTab => 'Posterior';
  @override
  String get anteriorChainLabel => 'Cadena Frontal';
  @override
  String get posteriorChainLabel => 'Cadena Posterior';
  @override
  String get recoveredStatus => 'Recuperado';
  @override
  String get recoveringStatus => 'Recuperando';
  @override
  String get fatiguedStatus => 'Fatigado';
  @override
  String get zoneUnderMev => 'Bajo MEV';
  @override
  String get zoneOptimalMav => 'MAV Óptimo';
  @override
  String get zoneNearMrv => 'Cerca de MRV';
  @override
  String get zoneOverMrv => 'Sobre MRV';
  @override
  String weeklySetsRange({required Object current, required Object min, required Object max}) => '$current / $min-$max series';
  @override
  String recoveryPercent({required Object percent}) => '$percent% Recuperación';
  @override
  String exploreMuscleExercises({required Object muscle}) => 'Explorar Ejercicios de $muscle';
  @override
  String get muscleRecoverySectionTitle => 'Recuperación Muscular';
  @override
  String readyCountBadge({required Object ready, required Object total}) => '$ready/$total Listos';
  @override
  String setsMevSummary({required Object sets, required Object mavMax, required Object mev}) => '$sets/$mavMax series · MEV $mev';
  @override
  String get estimated1rmSectionTitle => 'Récords de 1RM Estimado';
  @override
  String get noPrsYet => 'Completa series con peso para desbloquear tu 1RM.';
  @override
  String bestSetSubtitle({required Object weight, required Object reps}) => 'Mejor: ${weight}kg × $reps';
}

class _StringsWorkoutEs extends _StringsWorkout {
  @override
  String get finishButton => 'Finalizar';
  @override
  String get durationLabel => 'Duración';
  @override
  String get completedSetsLabel => 'Series Completadas';
  @override
  String get exercisesLabel => 'Ejercicios';
  @override
  String get addExerciseButton => 'Añadir Ejercicio';
  @override
  String get machineBusySwapPill => 'Máquina Ocupada · Cambiar';
  @override
  String get machineBusyModalTitle => 'Máquina Ocupada (Cambiar Ejercicio)';
  @override
  String ghostPaceCompare({required Object live, required Object target}) => 'Tú: $live kg · Ritmo Ghost: $target kg';
  @override
  String ghostAheadBadge({required Object delta}) => '+$delta kg Adelante';
  @override
  String ghostBehindBadge({required Object delta}) => '$delta kg Detrás';
  @override
  String get ghostOnPaceBadge => 'En Ritmo';
  @override
  String get anatomicalCardHeader => 'TARJETA ANATÓMICA DE ENTRENO';
  @override
  String ghostVerdictAhead({required Object delta}) => 'Veredicto Ghost: +$delta kg Adelante';
  @override
  String ghostVerdictBehind({required Object delta}) => 'Veredicto Ghost: $delta kg Detrás';
  @override
  String get ghostVerdictOnPace => 'Veredicto Ghost: En Ritmo';
  @override
  String get ghostVerdictCompleted => 'Veredicto Ghost: Completado';
  @override
  String get muscleActivationSectionTitle => 'MAPA DE ACTIVACIÓN MUSCULAR';
  @override
  String get copyShareCardButton => 'Copiar Tarjeta';
  @override
  String get doneButton => 'Listo';
  @override
  String get cardCopiedSnackbar => '¡Tarjeta anatómica copiada al portapapeles!';
}

class _StringsHybridAiEs extends _StringsHybridAi {
  @override
  String get aiCoachToggleChip => 'NPU Híbrido';
  @override
  String get routerTitle => 'Router IA Híbrido ATLAS';
  @override
  String npuStatusPrefix({required Object status}) => 'NPU AICore: $status';
  @override
  String get statusOnDeviceReady => 'Listo en Dispositivo';
  @override
  String get statusDownloadable => 'Descargable';
  @override
  String get statusDownloading => 'Descargando Modelo';
  @override
  String get statusCloudFallback => 'Respaldo en la Nube';
  @override
  String get sourceOnDeviceNano => 'EN DISPOSITIVO · Gemini Nano';
  @override
  String get sourceOnDeviceApple => 'EN DISPOSITIVO · Apple Intelligence';
  @override
  String get sourceOnDeviceChrome => 'EN DISPOSITIVO · Chrome Gemini Nano';
  @override
  String get sourceOnDeviceShort => 'EN DISPOSITIVO';
  @override
  String sourceInCloud({required Object model}) => 'EN LA NUBE · $model';
  @override
  String get sourceInCloudShort => 'EN LA NUBE';
  @override
  String get sourceOfflineEngine => 'MOTOR SIN CONEXIÓN';
  @override
  String get ramWarmedUp => 'RAM Precalentada';
  @override
  String get downloadModelButton => 'Descargar Modelo Local';
  @override
  String dotpromptBadge({required Object templateId}) => 'Dotprompt · $templateId';
  @override
  String remoteConfigOnlyBadge({required Object templateId}) => 'Solo Remote Config · $templateId';
  @override
  String get modeSectionTitle => 'Política de Ejecución (Firebase AI Logic InferenceMode)';
  @override
  String get modeSectionSubtitle => 'Enruta peticiones entre Gemini Nano local (AICore) y Cloud Gemini.';
  @override
  String get modePreferOnDevice => 'Preferir en Dispositivo';
  @override
  String get modeOnlyOnDevice => 'Solo en Dispositivo';
  @override
  String get modePreferInCloud => 'Preferir en la Nube';
  @override
  String get modeOnlyInCloud => 'Solo en la Nube';
  @override
  String get loggerTitle => 'Autorregulador de Series sin Conexión';
  @override
  String get loggerSubtitle => 'Registra series en lenguaje natural o escanea equipamiento sin latencia en la nube.';
  @override
  String get presetHeavyBenchChip => 'Press Banca Pesado (100kg x 6 @ RPE 9.5)';
  @override
  String get presetFastSquatChip => 'Sentadilla Rápida (120kg x 8 @ RPE 7.0)';
  @override
  String get inputHint => 'ej. Press de Banca con Barra 100kg x 6 @ RPE 9.5';
  @override
  String get analyzeSetButton => 'Analizar Serie';
  @override
  String get scanEquipmentButton => 'Escanear Equipo';
  @override
  String get loadLabel => 'CARGA';
  @override
  String get repsLabel => 'REPS';
  @override
  String get rpeLabel => 'RPE';
  @override
  String get fatigueAlertBadge => 'Alerta de Fatiga SNC';
  @override
  String get optimalVelocityBadge => 'Velocidad Óptima';
  @override
  String get visionCardTitle => 'Escaneo Multimodal de Equipamiento (Imagen + Prompt)';
  @override
  String get activeWorkoutSectionTitle => 'AUTORREGULACIÓN DE SERIE NPU HÍBRIDO';
  @override
  String get rpe7Chip => 'RPE 7 · +2.5kg';
  @override
  String get rpe85Chip => 'RPE 8.5 · Mantener';
  @override
  String get rpe95Chip => 'RPE 9.5 · -5% Carga';
  @override
  String get fatigueAlertBannerBadge => 'ALERTA DE FATIGA';
  @override
  String recHighFatigueWithWeight({required Object rpe, required Object weight}) =>
      'Alta fatiga del SNC detectada (RPE $rpe). Reduce la carga a ${weight}kg y descansa 180s antes de la siguiente serie.';
  @override
  String recHighFatigueNoWeight({required Object rpe}) =>
      'Alta fatiga del SNC detectada (RPE $rpe). Reduce la carga un 5% y descansa 180s antes de la siguiente serie.';
  @override
  String recNearFailureWithWeight({required Object rpe, required Object weight}) =>
      'Cerca del fallo muscular (RPE $rpe). Mantén ${weight}kg, prioriza la velocidad de barra y descansa 150-180s.';
  @override
  String recNearFailureNoWeight({required Object rpe}) =>
      'Cerca del fallo muscular (RPE $rpe). Mantén la carga actual y descansa 150-180s.';
  @override
  String recProgressiveOverload({required Object rpe, required Object weight, required Object reps}) =>
      'Gran velocidad de barra (RPE $rpe). Aplica sobrecarga progresiva: sube a ${weight}kg para $reps repeticiones.';
  @override
  String recOptimalWithWeight({required Object rpe, required Object weight, required Object reps}) =>
      'Zona óptima de hipertrofia (RPE $rpe). Mantén ${weight}kg para $reps repeticiones con 90-120s de descanso.';
  @override
  String recOptimalNoWeight({required Object rpe, required Object reps}) =>
      'Estímulo de entrenamiento óptimo (RPE $rpe). Mantén la carga para $reps repeticiones con 90-120s de descanso.';
  @override
  String errorOnlyOnDeviceUnavailable({required Object status}) =>
      'El modo Solo en Dispositivo requiere pesos NPU locales (estado actual: $status).';
}

// -----------------------------------------------------------------------------
// English (en)
// -----------------------------------------------------------------------------

class _TranslationsEn extends Translations {
  @override
  final _StringsCommon common = _StringsCommonEn();
  @override
  final _StringsDashboard dashboard = _StringsDashboardEn();
  @override
  final _StringsAiCoach aiCoach = _StringsAiCoachEn();
  @override
  final _StringsAnalytics analytics = _StringsAnalyticsEn();
  @override
  final _StringsWorkout workout = _StringsWorkoutEn();
  @override
  final _StringsHybridAi hybridAi = _StringsHybridAiEn();
}

class _StringsCommonEn extends _StringsCommon {
  @override
  String get appName => 'COMMUNITY FITNESS';
  @override
  String get language => 'Language';
  @override
  String get selectLanguage => 'Select Language';
  @override
  String get cancel => 'Cancel';
  @override
  String get close => 'Close';
  @override
  Map<String, String> get languages => const {'es': 'Español', 'en': 'English', 'ca': 'Català', 'fr': 'Français', 'pt': 'Português'};
}

class _StringsDashboardEn extends _StringsDashboard {
  @override
  String get aiCoachTooltip => 'ATLAS • AI Personal Trainer';
  @override
  String get dataManagementTooltip => 'Data Management';
  @override
  String get muscleAnalyticsTooltip => 'Muscle Analytics';
  @override
  String get languageTooltip => 'Change Language';
  @override
  String get readyToTrain => 'READY TO TRAIN';
  @override
  String workoutsThisWeek({required Object count}) => '$count workouts this week';
  @override
  String get freestyleTraining => 'Freestyle Training';
  @override
  String exercisesPlanned({required Object count}) => '$count exercises planned';
  @override
  String get buildOnTheFly => 'Build your session on the fly';
  @override
  String get totalSets => 'TOTAL SETS';
  @override
  String get movements => 'MOVEMENTS';
  @override
  String get targetIntensity => 'TARGET INTENSITY';
  @override
  String get startRoutine => 'Start Routine';
  @override
  String get startFreestyle => 'Start Freestyle';
  @override
  String get exploreAndManage => 'EXPLORE & MANAGE';
  @override
  String get routinesTitle => 'Routines';
  @override
  String routinesSubtitle({required Object count}) => '$count splits saved';
  @override
  String get muscleRecoveryTitle => 'Muscle Recovery';
  @override
  String muscleRecoverySubtitle({required Object count}) => '$count muscles ready';
  @override
  String get exerciseCatalogTitle => 'Exercise Catalog';
  @override
  String exerciseCatalogSubtitle({required Object count}) => '$count movements';
  @override
  String get dataMigrationTitle => 'Data Migration';
  @override
  String get dataMigrationSubtitle => 'Hevy / Strong / JSON';
  @override
  String get targetMusclesReady => 'TARGET MUSCLES READY';
  @override
  String get recentWorkouts => 'RECENT WORKOUTS';
  @override
  String get noWorkoutsYet => 'No workouts logged yet. Start your first session above!';
  @override
  String get workoutSession => 'Workout Session';
  @override
  String exercisesCount({required Object count}) => '$count exercises';
  @override
  String get deleteSessionTooltip => 'Delete session';
  @override
  String get deleteSessionConfirmTitle => 'Delete workout session?';
  @override
  String deleteSessionConfirmMessage({required Object title}) => '"$title" will be permanently removed from your recent workouts.';
  @override
  String get deleteSessionConfirmButton => 'Delete';
}

class _StringsAiCoachEn extends _StringsAiCoach {
  @override
  String get headerTitle => 'AI PERSONAL TRAINER';
  @override
  String get modelBadge => 'ATLAS • Biomechanical AI Coach';
  @override
  String get liveActive => 'ATLAS Live Active';
  @override
  String get liveVoiceToggle => 'Activate ATLAS Live';
  @override
  String get analyzingMovements => 'ATLAS is analyzing catalog movements...';
  @override
  String get youLabel => 'YOU';
  @override
  String get liveCoachBadge => 'ATLAS • LIVE';
  @override
  String get flashCoachBadge => 'ATLAS • AI COACH';
  @override
  String get startAiWorkoutNow => 'Start This AI Workout Now';
  @override
  String setsRepsRest({required Object sets, required Object reps, required Object rest}) => '$sets sets × $reps reps • ${rest}s rest';
  @override
  String get form3dBadge => '3D Form';
  @override
  String get formDemoBadge => 'Demo';
  @override
  String welcomeMessage({required Object chatModel, required Object liveModel}) =>
      'Hi! I am ATLAS, your CommunityFitness AI Personal Trainer. Select the muscles you want to train, or ask for a no-weights home alternative for any exercise in the catalog!';
  @override
  final _StringsAiCoachLiveBanner liveBanner = _StringsAiCoachLiveBannerEn();
  @override
  final _StringsAiCoachContextCard contextCard = _StringsAiCoachContextCardEn();
  @override
  final _StringsAiCoachPlannerCard plannerCard = _StringsAiCoachPlannerCardEn();
  @override
  final _StringsAiCoachAlternativesSheet alternativesSheet = _StringsAiCoachAlternativesSheetEn();
  @override
  final _StringsAiCoachChatInput chatInput = _StringsAiCoachChatInputEn();
  @override
  Map<String, String> get muscles => const {
    'Chest': 'Chest',
    'Back': 'Back',
    'Shoulders': 'Shoulders',
    'Biceps': 'Biceps',
    'Triceps': 'Triceps',
    'Quadriceps': 'Quadriceps',
    'Quads': 'Quads',
    'Hamstrings': 'Hamstrings',
    'Glutes': 'Glutes',
    'Calves': 'Calves',
    'Abs / Core': 'Abs / Core',
    'Core': 'Core',
    'Legs': 'Legs',
    'Arms': 'Arms',
    'Full Body': 'Full Body',
  };
  @override
  Map<String, String> get equipment => const {
    'All': 'All',
    'Home / Bodyweight': 'Home / Bodyweight',
    'Dumbbells Only': 'Dumbbells Only',
    'Bodyweight': 'Bodyweight',
    'Barbell': 'Barbell',
    'Dumbbell': 'Dumbbell',
    'Machine': 'Machine',
    'Cable': 'Cable',
    'Kettlebell': 'Kettlebell',
  };
  @override
  Map<String, String> get constraints => const {
    'At Home / No Weights': 'At Home / No Weights',
    'Bodyweight Only': 'Bodyweight Only',
    'Dumbbells Only': 'Dumbbells Only',
    'Joint Friendly': 'Joint Friendly',
  };
  @override
  final _StringsAiCoachErrors errors = _StringsAiCoachErrorsEn();
}

class _StringsAiCoachLiveBannerEn extends _StringsAiCoachLiveBanner {
  @override
  String get listeningMic => 'LISTENING TO YOUR MIC — SPEAK TO ATLAS';
  @override
  String get connecting => 'CONNECTING TO ATLAS LIVE...';
  @override
  String get listening => 'LISTENING • SPEAK OR TAP A VOICE COMMAND';
  @override
  String get thinking => 'THINKING • REAL-TIME BIOMECHANICAL REASONING';
  @override
  String get speaking => 'ATLAS SPEAKING ALOUD • LIVE';
  @override
  String get disconnected => 'DISCONNECTED';
  @override
  String get defaultHint => 'Ask your Live Personal Trainer for real-time voice cues or home exercise swaps.';
  @override
  String get endSessionTooltip => 'End Live Voice Session';
  @override
  String get quickChipChestAbs => 'Home Chest & Abs (No Weights)';
  @override
  String get quickPromptChestAbs => 'Give me a chest and abs workout at home with no weights';
  @override
  String get quickChipBackBiceps => 'Back & Biceps at Home';
  @override
  String get quickPromptBackBiceps => 'Plan a back and biceps workout at home';
  @override
  String get quickChipLegsGlutes => 'Legs & Glutes Bodyweight';
  @override
  String get quickPromptLegsGlutes => 'Build a legs and glutes bodyweight routine';
}

class _StringsAiCoachContextCardEn extends _StringsAiCoachContextCard {
  @override
  String targetExercise({required Object name}) => 'TARGET EXERCISE: $name';
  @override
  String get subtitle => 'Need an alternative because you are training at home or missing equipment? Tap a constraint:';
}

class _StringsAiCoachPlannerCardEn extends _StringsAiCoachPlannerCard {
  @override
  String get title => 'WHAT MUSCLES DO YOU WANT TO TRAIN TODAY?';
  @override
  String get availableEquipment => 'AVAILABLE EQUIPMENT';
  @override
  String buildPlanButton({required Object muscles, required Object equipment}) => 'Build $muscles Plan ($equipment)';
}

class _StringsAiCoachAlternativesSheetEn extends _StringsAiCoachAlternativesSheet {
  @override
  String title({required Object name}) => 'AI Alternatives for $name';
  @override
  String get customHint => 'Custom note (e.g., at home with chair, sore wrists)...';
}

class _StringsAiCoachChatInputEn extends _StringsAiCoachChatInput {
  @override
  String get listeningHint => 'Listening to your microphone... Tap red button to send';
  @override
  String get liveHint => 'Tap mic to speak or type to ATLAS Live...';
  @override
  String get defaultHint => 'Ask for home alternatives or tap mic to speak...';
  @override
  String get sendTooltip => 'Send Message';
  @override
  String get stopMicTooltip => 'Stop Recording & Send Voice Turn';
  @override
  String get startMicTooltip => 'Record Voice Input (16kHz PCM)';
}

class _StringsAiCoachErrorsEn extends _StringsAiCoachErrors {
  @override
  String get loadAlternatives => 'Unable to load alternatives right now.';
  @override
  String get buildPlan => 'Unable to build workout plan right now.';
  @override
  String get coachReply => 'Coach could not respond right now.';
}

class _StringsAnalyticsEn extends _StringsAnalytics {
  @override
  String get screenTitle => 'Muscle Balance & Recovery';
  @override
  String get workoutsTitle => 'Workouts';
  @override
  String get thisWeekSubtitle => 'This week';
  @override
  String get volumeTitle => 'Volume';
  @override
  String get bodyMapTitle => '3D Anatomical Volume Map';
  @override
  String get frontViewTab => 'Front';
  @override
  String get backViewTab => 'Back';
  @override
  String get anteriorChainLabel => 'Front Chain';
  @override
  String get posteriorChainLabel => 'Back Chain';
  @override
  String get recoveredStatus => 'Recovered';
  @override
  String get recoveringStatus => 'Recovering';
  @override
  String get fatiguedStatus => 'Fatigued';
  @override
  String get zoneUnderMev => 'Under MEV';
  @override
  String get zoneOptimalMav => 'Optimal MAV';
  @override
  String get zoneNearMrv => 'Near MRV';
  @override
  String get zoneOverMrv => 'Over MRV';
  @override
  String weeklySetsRange({required Object current, required Object min, required Object max}) => '$current / $min-$max sets';
  @override
  String recoveryPercent({required Object percent}) => '$percent% Recovery';
  @override
  String exploreMuscleExercises({required Object muscle}) => 'Explore $muscle Exercises';
  @override
  String get muscleRecoverySectionTitle => 'Muscle Recovery';
  @override
  String readyCountBadge({required Object ready, required Object total}) => '$ready/$total Ready';
  @override
  String setsMevSummary({required Object sets, required Object mavMax, required Object mev}) => '$sets/$mavMax sets · MEV $mev';
  @override
  String get estimated1rmSectionTitle => 'Estimated 1RM Records';
  @override
  String get noPrsYet => 'Complete weighted sets to unlock 1RM estimates.';
  @override
  String bestSetSubtitle({required Object weight, required Object reps}) => 'Best: ${weight}kg × $reps';
}

class _StringsWorkoutEn extends _StringsWorkout {
  @override
  String get finishButton => 'Finish';
  @override
  String get durationLabel => 'Duration';
  @override
  String get completedSetsLabel => 'Completed Sets';
  @override
  String get exercisesLabel => 'Exercises';
  @override
  String get addExerciseButton => 'Add Exercise';
  @override
  String get machineBusySwapPill => 'Machine Busy · Swap';
  @override
  String get machineBusyModalTitle => 'Machine Busy (Swap Exercise)';
  @override
  String ghostPaceCompare({required Object live, required Object target}) => 'You: $live kg · Ghost pace: $target kg';
  @override
  String ghostAheadBadge({required Object delta}) => '+$delta kg Ahead';
  @override
  String ghostBehindBadge({required Object delta}) => '$delta kg Behind';
  @override
  String get ghostOnPaceBadge => 'On Pace';
  @override
  String get anatomicalCardHeader => 'ANATOMICAL WORKOUT CARD';
  @override
  String ghostVerdictAhead({required Object delta}) => 'Ghost Verdict: +$delta kg Ahead';
  @override
  String ghostVerdictBehind({required Object delta}) => 'Ghost Verdict: $delta kg Behind';
  @override
  String get ghostVerdictOnPace => 'Ghost Verdict: On Pace';
  @override
  String get ghostVerdictCompleted => 'Ghost Verdict: Completed';
  @override
  String get muscleActivationSectionTitle => 'MUSCLE ACTIVATION MAP';
  @override
  String get copyShareCardButton => 'Copy Share Card';
  @override
  String get doneButton => 'Done';
  @override
  String get cardCopiedSnackbar => 'Anatomical card copied to clipboard!';
}

class _StringsHybridAiEn extends _StringsHybridAi {
  @override
  String get aiCoachToggleChip => 'Hybrid NPU';
  @override
  String get routerTitle => 'ATLAS Hybrid AI Router';
  @override
  String npuStatusPrefix({required Object status}) => 'AICore NPU: $status';
  @override
  String get statusOnDeviceReady => 'On-Device Ready';
  @override
  String get statusDownloadable => 'Downloadable';
  @override
  String get statusDownloading => 'Downloading Model';
  @override
  String get statusCloudFallback => 'Cloud Fallback';
  @override
  String get sourceOnDeviceNano => 'ON-DEVICE · Gemini Nano';
  @override
  String get sourceOnDeviceApple => 'ON-DEVICE · Apple Intelligence';
  @override
  String get sourceOnDeviceChrome => 'ON-DEVICE · Chrome Gemini Nano';
  @override
  String get sourceOnDeviceShort => 'ON-DEVICE';
  @override
  String sourceInCloud({required Object model}) => 'IN-CLOUD · $model';
  @override
  String get sourceInCloudShort => 'IN-CLOUD';
  @override
  String get sourceOfflineEngine => 'OFFLINE ENGINE';
  @override
  String get ramWarmedUp => 'RAM Warmed Up';
  @override
  String get downloadModelButton => 'Download On-Device Model';
  @override
  String dotpromptBadge({required Object templateId}) => 'Dotprompt · $templateId';
  @override
  String remoteConfigOnlyBadge({required Object templateId}) => 'Remote Config Only · $templateId';
  @override
  String get modeSectionTitle => 'Execution Policy (Firebase AI Logic InferenceMode)';
  @override
  String get modeSectionSubtitle => 'Route requests between local Gemini Nano (AICore) and Cloud Gemini.';
  @override
  String get modePreferOnDevice => 'Prefer On-Device';
  @override
  String get modeOnlyOnDevice => 'Only On-Device';
  @override
  String get modePreferInCloud => 'Prefer in Cloud';
  @override
  String get modeOnlyInCloud => 'Only in Cloud';
  @override
  String get loggerTitle => 'Basement Gym Offline-First Set Autoregulator';
  @override
  String get loggerSubtitle => 'Log sets in natural language or scan equipment with zero cloud latency.';
  @override
  String get presetHeavyBenchChip => 'Heavy Bench (100kg x 6 @ RPE 9.5)';
  @override
  String get presetFastSquatChip => 'Fast Squat (120kg x 8 @ RPE 7.0)';
  @override
  String get inputHint => 'e.g. Barbell Bench Press 100kg x 6 @ RPE 9.5';
  @override
  String get analyzeSetButton => 'Analyze Set';
  @override
  String get scanEquipmentButton => 'Scan Equipment';
  @override
  String get loadLabel => 'LOAD';
  @override
  String get repsLabel => 'REPS';
  @override
  String get rpeLabel => 'RPE';
  @override
  String get fatigueAlertBadge => 'CNS Fatigue Alert';
  @override
  String get optimalVelocityBadge => 'Optimal Velocity';
  @override
  String get visionCardTitle => 'Multimodal Equipment Scan (Bitmap + Prompt)';
  @override
  String get activeWorkoutSectionTitle => 'HYBRID NPU SET AUTOREGULATION';
  @override
  String get rpe7Chip => 'RPE 7 · +2.5kg';
  @override
  String get rpe85Chip => 'RPE 8.5 · Keep';
  @override
  String get rpe95Chip => 'RPE 9.5 · -5% Load';
  @override
  String get fatigueAlertBannerBadge => 'FATIGUE ALERT';
  @override
  String recHighFatigueWithWeight({required Object rpe, required Object weight}) =>
      'High CNS fatigue detected (RPE $rpe). Reduce load to ${weight}kg and rest 180s before the next set.';
  @override
  String recHighFatigueNoWeight({required Object rpe}) =>
      'High CNS fatigue detected (RPE $rpe). Reduce load by 5% and rest 180s before the next set.';
  @override
  String recNearFailureWithWeight({required Object rpe, required Object weight}) =>
      'Near muscular failure (RPE $rpe). Maintain ${weight}kg, focus on bar speed, and rest 150-180s.';
  @override
  String recNearFailureNoWeight({required Object rpe}) =>
      'Near muscular failure (RPE $rpe). Maintain current load and rest 150-180s.';
  @override
  String recProgressiveOverload({required Object rpe, required Object weight, required Object reps}) =>
      'Strong bar velocity (RPE $rpe). Apply progressive overload: increase to ${weight}kg for $reps reps.';
  @override
  String recOptimalWithWeight({required Object rpe, required Object weight, required Object reps}) =>
      'Optimal hypertrophy zone (RPE $rpe). Keep ${weight}kg for $reps reps with 90-120s rest.';
  @override
  String recOptimalNoWeight({required Object rpe, required Object reps}) =>
      'Optimal training stimulus (RPE $rpe). Maintain load for $reps reps with 90-120s rest.';
  @override
  String errorOnlyOnDeviceUnavailable({required Object status}) =>
      'Only On-Device mode requires local NPU weights (current status: $status).';
}

// -----------------------------------------------------------------------------
// Català (ca)
// -----------------------------------------------------------------------------

class _TranslationsCa extends Translations {
  @override
  final _StringsCommon common = _StringsCommonCa();
  @override
  final _StringsDashboard dashboard = _StringsDashboardCa();
  @override
  final _StringsAiCoach aiCoach = _StringsAiCoachCa();
  @override
  final _StringsAnalytics analytics = _StringsAnalyticsCa();
  @override
  final _StringsWorkout workout = _StringsWorkoutCa();
  @override
  final _StringsHybridAi hybridAi = _StringsHybridAiCa();
}

class _StringsCommonCa extends _StringsCommon {
  @override
  String get appName => 'COMMUNITY FITNESS';
  @override
  String get language => 'Idioma';
  @override
  String get selectLanguage => 'Seleccionar Idioma';
  @override
  String get cancel => 'Cancel·lar';
  @override
  String get close => 'Tancar';
  @override
  Map<String, String> get languages => const {'es': 'Español', 'en': 'English', 'ca': 'Català', 'fr': 'Français', 'pt': 'Português'};
}

class _StringsDashboardCa extends _StringsDashboard {
  @override
  String get aiCoachTooltip => 'ATLAS • Entrenador Personal IA';
  @override
  String get dataManagementTooltip => 'Gestió de Dades';
  @override
  String get muscleAnalyticsTooltip => 'Analítica Muscular';
  @override
  String get languageTooltip => 'Canviar Idioma';
  @override
  String get readyToTrain => 'LLEST PER ENTRENAR';
  @override
  String workoutsThisWeek({required Object count}) => '$count entrenaments aquesta setmana';
  @override
  String get freestyleTraining => 'Entrenament Lliure';
  @override
  String exercisesPlanned({required Object count}) => '$count exercicis planificats';
  @override
  String get buildOnTheFly => 'Crea la teva sessió al moment';
  @override
  String get totalSets => 'SÈRIES TOTALS';
  @override
  String get movements => 'MOVIMENTS';
  @override
  String get targetIntensity => 'INTENSITAT OBJECTIU';
  @override
  String get startRoutine => 'Iniciar Rutina';
  @override
  String get startFreestyle => 'Entrenament Lliure';
  @override
  String get exploreAndManage => 'EXPLORAR I GESTIONAR';
  @override
  String get routinesTitle => 'Rutines';
  @override
  String routinesSubtitle({required Object count}) => '$count rutines desades';
  @override
  String get muscleRecoveryTitle => 'Recuperació Muscular';
  @override
  String muscleRecoverySubtitle({required Object count}) => '$count músculs llestos';
  @override
  String get exerciseCatalogTitle => "Catàleg d'Exercicis";
  @override
  String exerciseCatalogSubtitle({required Object count}) => '$count moviments';
  @override
  String get dataMigrationTitle => 'Migració de Dades';
  @override
  String get dataMigrationSubtitle => 'Hevy / Strong / JSON';
  @override
  String get targetMusclesReady => 'MÚSCULS LLESTOS PER AVUI';
  @override
  String get recentWorkouts => 'ENTRENAMENTS RECENTS';
  @override
  String get noWorkoutsYet => 'Encara no hi ha entrenaments registrats. Comença la teva primera sessió a dalt!';
  @override
  String get workoutSession => "Sessió d'Entrenament";
  @override
  String exercisesCount({required Object count}) => '$count exercicis';
  @override
  String get deleteSessionTooltip => 'Eliminar sessió';
  @override
  String get deleteSessionConfirmTitle => 'Eliminar entrenament?';
  @override
  String deleteSessionConfirmMessage({required Object title}) =>
      'S\'eliminarà "$title" dels teus entrenaments recents. Aquesta acció no es pot desfer.';
  @override
  String get deleteSessionConfirmButton => 'Eliminar';
}

class _StringsAiCoachCa extends _StringsAiCoach {
  @override
  String get headerTitle => 'ENTRENADOR PERSONAL IA';
  @override
  String get modelBadge => 'ATLAS • Entrenador Biomecànic IA';
  @override
  String get liveActive => 'ATLAS En Viu Actiu';
  @override
  String get liveVoiceToggle => 'Activar ATLAS Live';
  @override
  String get analyzingMovements => 'ATLAS està analitzant moviments del catàleg...';
  @override
  String get youLabel => 'TU';
  @override
  String get liveCoachBadge => 'ATLAS • EN VIU';
  @override
  String get flashCoachBadge => 'ATLAS • COACH IA';
  @override
  String get startAiWorkoutNow => 'Començar Aquest Entrenament IA Ara';
  @override
  String setsRepsRest({required Object sets, required Object reps, required Object rest}) => '$sets sèries × $reps reps • ${rest}s descans';
  @override
  String get form3dBadge => 'Forma 3D';
  @override
  String get formDemoBadge => 'Demo';
  @override
  String welcomeMessage({required Object chatModel, required Object liveModel}) =>
      'Hola! Sóc ATLAS, el teu Entrenador Personal IA de CommunityFitness. Selecciona els músculs que vols entrenar o demana alternatives a casa sense peses per a qualsevol exercici del catàleg!';
  @override
  final _StringsAiCoachLiveBanner liveBanner = _StringsAiCoachLiveBannerCa();
  @override
  final _StringsAiCoachContextCard contextCard = _StringsAiCoachContextCardCa();
  @override
  final _StringsAiCoachPlannerCard plannerCard = _StringsAiCoachPlannerCardCa();
  @override
  final _StringsAiCoachAlternativesSheet alternativesSheet = _StringsAiCoachAlternativesSheetCa();
  @override
  final _StringsAiCoachChatInput chatInput = _StringsAiCoachChatInputCa();
  @override
  Map<String, String> get muscles => const {
    'Chest': 'Pit',
    'Back': 'Esquena',
    'Shoulders': 'Espatlles',
    'Biceps': 'Bíceps',
    'Triceps': 'Tríceps',
    'Quadriceps': 'Quàdriceps',
    'Quads': 'Quàdriceps',
    'Hamstrings': 'Isquiotibials',
    'Glutes': 'Glutis',
    'Calves': 'Bessons',
    'Abs / Core': 'Abdomen / Core',
    'Core': 'Core',
    'Legs': 'Cames',
    'Arms': 'Braços',
    'Full Body': 'Cos Complet',
  };
  @override
  Map<String, String> get equipment => const {
    'All': 'Tot',
    'Home / Bodyweight': 'A Casa / Pes Corporal',
    'Dumbbells Only': 'Només Manuelles',
    'Bodyweight': 'Pes Corporal',
    'Barbell': 'Barra',
    'Dumbbell': 'Manuella',
    'Machine': 'Màquina',
    'Cable': 'Politja',
    'Kettlebell': 'Kettlebell',
  };
  @override
  Map<String, String> get constraints => const {
    'At Home / No Weights': 'A Casa / Sense Peses',
    'Bodyweight Only': 'Només Pes Corporal',
    'Dumbbells Only': 'Només Manuelles',
    'Joint Friendly': 'Cura Articular',
  };
  @override
  final _StringsAiCoachErrors errors = _StringsAiCoachErrorsCa();
}

class _StringsAiCoachLiveBannerCa extends _StringsAiCoachLiveBanner {
  @override
  String get listeningMic => 'ESCOLTANT EL TEU MICRÒFON — PARLA AMB ATLAS';
  @override
  String get connecting => 'CONNECTANT AMB ATLAS EN VIU...';
  @override
  String get listening => 'ESCOLTANT • PARLA O UTILITZA UN COMANDAMENT DE VEU';
  @override
  String get thinking => 'PENSANT • RAONAMENT BIOMECÀNIC EN TEMPS REAL';
  @override
  String get speaking => 'ATLAS ESTÀ PARLANT • EN VIU';
  @override
  String get disconnected => 'DESCONNECTAT';
  @override
  String get defaultHint => "Demana al teu Entrenador Personal en Viu indicacions de veu en temps real o canvis d'exercicis per fer a casa.";
  @override
  String get endSessionTooltip => 'Finalitzar Sessió de Veu en Viu';
  @override
  String get quickChipChestAbs => 'Pit i Abdomen a Casa (Sense Peses)';
  @override
  String get quickPromptChestAbs => "Dona'm una rutina de pit i abdominals a casa sense peses";
  @override
  String get quickChipBackBiceps => 'Esquena i Bíceps a Casa';
  @override
  String get quickPromptBackBiceps => "Planifica un entrenament d'esquena i bíceps a casa";
  @override
  String get quickChipLegsGlutes => 'Cames i Glutis Pes Corporal';
  @override
  String get quickPromptLegsGlutes => 'Crea una rutina de cames i glutis amb pes corporal';
}

class _StringsAiCoachContextCardCa extends _StringsAiCoachContextCard {
  @override
  String targetExercise({required Object name}) => 'EXERCICI OBJECTIU: $name';
  @override
  String get subtitle => 'Necessites una alternativa perquè entrenes a casa o et falta material? Toca una opció:';
}

class _StringsAiCoachPlannerCardCa extends _StringsAiCoachPlannerCard {
  @override
  String get title => 'QUINS MÚSCULS VOLS ENTRENAR AVUI?';
  @override
  String get availableEquipment => 'EQUIPAMENT DISPONIBLE';
  @override
  String buildPlanButton({required Object muscles, required Object equipment}) => 'Crear Pla de $muscles ($equipment)';
}

class _StringsAiCoachAlternativesSheetCa extends _StringsAiCoachAlternativesSheet {
  @override
  String title({required Object name}) => 'Alternatives IA per a $name';
  @override
  String get customHint => 'Nota personalitzada (ex. a casa amb cadira, mal de canell)...';
}

class _StringsAiCoachChatInputCa extends _StringsAiCoachChatInput {
  @override
  String get listeningHint => 'Escoltant el teu micròfon... Toca el botó vermell per enviar';
  @override
  String get liveHint => 'Toca el mic per parlar o escriu a ATLAS Live...';
  @override
  String get defaultHint => 'Demana alternatives a casa o toca el mic per parlar...';
  @override
  String get sendTooltip => 'Enviar Missatge';
  @override
  String get stopMicTooltip => 'Aturar Gravació i Enviar Veu';
  @override
  String get startMicTooltip => 'Gravar Veu (16kHz PCM)';
}

class _StringsAiCoachErrorsCa extends _StringsAiCoachErrors {
  @override
  String get loadAlternatives => "No s'han pogut carregar les alternatives en aquest moment.";
  @override
  String get buildPlan => "No s'ha pogut crear el pla d'entrenament en aquest moment.";
  @override
  String get coachReply => "L'entrenador no ha pogut respondre en aquest moment.";
}

class _StringsAnalyticsCa extends _StringsAnalytics {
  @override
  String get screenTitle => 'Balanç i Recuperació Muscular';
  @override
  String get workoutsTitle => 'Entrenaments';
  @override
  String get thisWeekSubtitle => 'Aquesta setmana';
  @override
  String get volumeTitle => 'Volum';
  @override
  String get bodyMapTitle => 'Mapa Anatòmic de Volum 3D';
  @override
  String get frontViewTab => 'Frontal';
  @override
  String get backViewTab => 'Posterior';
  @override
  String get anteriorChainLabel => 'Cadena Frontal';
  @override
  String get posteriorChainLabel => 'Cadena Posterior';
  @override
  String get recoveredStatus => 'Recuperat';
  @override
  String get recoveringStatus => 'Recuperant';
  @override
  String get fatiguedStatus => 'Fatigat';
  @override
  String get zoneUnderMev => 'Sota MEV';
  @override
  String get zoneOptimalMav => 'MAV Òptim';
  @override
  String get zoneNearMrv => 'Prop de MRV';
  @override
  String get zoneOverMrv => 'Sobre MRV';
  @override
  String weeklySetsRange({required Object current, required Object min, required Object max}) => '$current / $min-$max sèries';
  @override
  String recoveryPercent({required Object percent}) => '$percent% Recuperació';
  @override
  String exploreMuscleExercises({required Object muscle}) => 'Explorar Exercicis de $muscle';
  @override
  String get muscleRecoverySectionTitle => 'Recuperació Muscular';
  @override
  String readyCountBadge({required Object ready, required Object total}) => '$ready/$total Llestos';
  @override
  String setsMevSummary({required Object sets, required Object mavMax, required Object mev}) => '$sets/$mavMax sèries · MEV $mev';
  @override
  String get estimated1rmSectionTitle => "Rècords d'1RM Estimat";
  @override
  String get noPrsYet => 'Completa sèries amb pes per desbloquejar el teu 1RM.';
  @override
  String bestSetSubtitle({required Object weight, required Object reps}) => 'Millor: ${weight}kg × $reps';
}

class _StringsWorkoutCa extends _StringsWorkout {
  @override
  String get finishButton => 'Finalitzar';
  @override
  String get durationLabel => 'Durada';
  @override
  String get completedSetsLabel => 'Sèries Completades';
  @override
  String get exercisesLabel => 'Exercicis';
  @override
  String get addExerciseButton => 'Afegir Exercici';
  @override
  String get machineBusySwapPill => 'Màquina Ocupada · Canviar';
  @override
  String get machineBusyModalTitle => 'Màquina Ocupada (Canviar Exercici)';
  @override
  String ghostPaceCompare({required Object live, required Object target}) => 'Tu: $live kg · Ritme Ghost: $target kg';
  @override
  String ghostAheadBadge({required Object delta}) => '+$delta kg Per Davant';
  @override
  String ghostBehindBadge({required Object delta}) => '$delta kg Per Darrere';
  @override
  String get ghostOnPaceBadge => 'Al Ritme';
  @override
  String get anatomicalCardHeader => "TARGETA ANATÒMICA D'ENTRENAMENT";
  @override
  String ghostVerdictAhead({required Object delta}) => 'Veredicte Ghost: +$delta kg Per Davant';
  @override
  String ghostVerdictBehind({required Object delta}) => 'Veredicte Ghost: $delta kg Per Darrere';
  @override
  String get ghostVerdictOnPace => 'Veredicte Ghost: Al Ritme';
  @override
  String get ghostVerdictCompleted => 'Veredicte Ghost: Completat';
  @override
  String get muscleActivationSectionTitle => "MAPA D'ACTIVACIÓ MUSCULAR";
  @override
  String get copyShareCardButton => 'Copiar Targeta';
  @override
  String get doneButton => 'Fet';
  @override
  String get cardCopiedSnackbar => 'Targeta anatòmica copiada al porta-retalls!';
}

class _StringsHybridAiCa extends _StringsHybridAi {
  @override
  String get aiCoachToggleChip => 'NPU Híbrid';
  @override
  String get routerTitle => 'Encaminador IA Híbrid ATLAS';
  @override
  String npuStatusPrefix({required Object status}) => 'NPU AICore: $status';
  @override
  String get statusOnDeviceReady => 'Llest al Dispositiu';
  @override
  String get statusDownloadable => 'Descarregable';
  @override
  String get statusDownloading => 'Descarregant Model';
  @override
  String get statusCloudFallback => 'Respatller al Núvol';
  @override
  String get sourceOnDeviceNano => 'AL DISPOSITIU · Gemini Nano';
  @override
  String get sourceOnDeviceApple => 'AL DISPOSITIU · Apple Intelligence';
  @override
  String get sourceOnDeviceChrome => 'AL DISPOSITIU · Chrome Gemini Nano';
  @override
  String get sourceOnDeviceShort => 'AL DISPOSITIU';
  @override
  String sourceInCloud({required Object model}) => 'AL NÚVOL · $model';
  @override
  String get sourceInCloudShort => 'AL NÚVOL';
  @override
  String get sourceOfflineEngine => 'MOTOR FORA DE LÍNIA';
  @override
  String get ramWarmedUp => 'RAM Preescalfada';
  @override
  String get downloadModelButton => 'Descarregar Model Local';
  @override
  String dotpromptBadge({required Object templateId}) => 'Dotprompt · $templateId';
  @override
  String remoteConfigOnlyBadge({required Object templateId}) => 'Només Remote Config · $templateId';
  @override
  String get modeSectionTitle => "Política d'Execució (Firebase AI Logic InferenceMode)";
  @override
  String get modeSectionSubtitle => 'Encamina peticions entre Gemini Nano local (AICore) i Cloud Gemini.';
  @override
  String get modePreferOnDevice => 'Preferir al Dispositiu';
  @override
  String get modeOnlyOnDevice => 'Només al Dispositiu';
  @override
  String get modePreferInCloud => 'Preferir al Núvol';
  @override
  String get modeOnlyInCloud => 'Només al Núvol';
  @override
  String get loggerTitle => 'Autoregulador de Sèries sense Connexió';
  @override
  String get loggerSubtitle => 'Registra sèries en llenguatge natural o escaneja equipament sense latència al núvol.';
  @override
  String get presetHeavyBenchChip => 'Press Banca Pesant (100kg x 6 @ RPE 9.5)';
  @override
  String get presetFastSquatChip => 'Esquat Ràpid (120kg x 8 @ RPE 7.0)';
  @override
  String get inputHint => 'ex. Press de Banca amb Barra 100kg x 6 @ RPE 9.5';
  @override
  String get analyzeSetButton => 'Analitzar Sèrie';
  @override
  String get scanEquipmentButton => 'Escanejar Equip';
  @override
  String get loadLabel => 'CÀRREGA';
  @override
  String get repsLabel => 'REPS';
  @override
  String get rpeLabel => 'RPE';
  @override
  String get fatigueAlertBadge => 'Alerta de Fatiga SNC';
  @override
  String get optimalVelocityBadge => 'Velocitat Òptima';
  @override
  String get visionCardTitle => "Escaneig Multimodal d'Equipament (Imatge + Prompt)";
  @override
  String get activeWorkoutSectionTitle => 'AUTOREGULACIÓ DE SÈRIE NPU HÍBRID';
  @override
  String get rpe7Chip => 'RPE 7 · +2.5kg';
  @override
  String get rpe85Chip => 'RPE 8.5 · Mantenir';
  @override
  String get rpe95Chip => 'RPE 9.5 · -5% Càrrega';
  @override
  String get fatigueAlertBannerBadge => 'ALERTA DE FATIGA';
  @override
  String recHighFatigueWithWeight({required Object rpe, required Object weight}) =>
      'Alta fatiga del SNC detectada (RPE $rpe). Redueix la càrrega a ${weight}kg i descansa 180s abans de la següent sèrie.';
  @override
  String recHighFatigueNoWeight({required Object rpe}) =>
      'Alta fatiga del SNC detectada (RPE $rpe). Redueix la càrrega un 5% i descansa 180s abans de la següent sèrie.';
  @override
  String recNearFailureWithWeight({required Object rpe, required Object weight}) =>
      'A prop de la fallada muscular (RPE $rpe). Mantén ${weight}kg, prioritza la velocitat de barra i descansa 150-180s.';
  @override
  String recNearFailureNoWeight({required Object rpe}) =>
      'A prop de la fallada muscular (RPE $rpe). Mantén la càrrega actual i descansa 150-180s.';
  @override
  String recProgressiveOverload({required Object rpe, required Object weight, required Object reps}) =>
      'Gran velocitat de barra (RPE $rpe). Aplica sobrecàrrega progressiva: puja a ${weight}kg per a $reps repeticions.';
  @override
  String recOptimalWithWeight({required Object rpe, required Object weight, required Object reps}) =>
      "Zona òptima d'hipertròfia (RPE $rpe). Mantén ${weight}kg per a $reps repeticions amb 90-120s de descans.";
  @override
  String recOptimalNoWeight({required Object rpe, required Object reps}) =>
      "Estímul d'entrenament òptim (RPE $rpe). Mantén la càrrega per a $reps repeticions amb 90-120s de descans.";
  @override
  String errorOnlyOnDeviceUnavailable({required Object status}) =>
      'El mode Només al Dispositiu requereix pesos NPU locals (estat actual: $status).';
}

// -----------------------------------------------------------------------------
// Français (fr)
// -----------------------------------------------------------------------------

class _TranslationsFr extends Translations {
  @override
  final _StringsCommon common = _StringsCommonFr();
  @override
  final _StringsDashboard dashboard = _StringsDashboardFr();
  @override
  final _StringsAiCoach aiCoach = _StringsAiCoachFr();
  @override
  final _StringsAnalytics analytics = _StringsAnalyticsFr();
  @override
  final _StringsWorkout workout = _StringsWorkoutFr();
  @override
  final _StringsHybridAi hybridAi = _StringsHybridAiFr();
}

class _StringsCommonFr extends _StringsCommon {
  @override
  String get appName => 'COMMUNITY FITNESS';
  @override
  String get language => 'Langue';
  @override
  String get selectLanguage => 'Choisir la Langue';
  @override
  String get cancel => 'Annuler';
  @override
  String get close => 'Fermer';
  @override
  Map<String, String> get languages => const {'es': 'Español', 'en': 'English', 'ca': 'Català', 'fr': 'Français', 'pt': 'Português'};
}

class _StringsDashboardFr extends _StringsDashboard {
  @override
  String get aiCoachTooltip => 'ATLAS • Coach Personnel IA';
  @override
  String get dataManagementTooltip => 'Gestion des Données';
  @override
  String get muscleAnalyticsTooltip => 'Analyse Musculaire';
  @override
  String get languageTooltip => 'Changer de Langue';
  @override
  String get readyToTrain => "PRÊT À S'ENTRAÎNER";
  @override
  String workoutsThisWeek({required Object count}) => '$count séances cette semaine';
  @override
  String get freestyleTraining => 'Entraînement Libre';
  @override
  String exercisesPlanned({required Object count}) => '$count exercices prévus';
  @override
  String get buildOnTheFly => 'Créez votre séance à la volée';
  @override
  String get totalSets => 'SÉRIES TOTALES';
  @override
  String get movements => 'MOUVEMENTS';
  @override
  String get targetIntensity => 'INTENSITÉ CIBLE';
  @override
  String get startRoutine => 'Démarrer la Routine';
  @override
  String get startFreestyle => 'Entraînement Libre';
  @override
  String get exploreAndManage => 'EXPLORER ET GÉRER';
  @override
  String get routinesTitle => 'Routines';
  @override
  String routinesSubtitle({required Object count}) => '$count programmes enregistrés';
  @override
  String get muscleRecoveryTitle => 'Récupération Musculaire';
  @override
  String muscleRecoverySubtitle({required Object count}) => '$count muscles prêts';
  @override
  String get exerciseCatalogTitle => "Catalogue d'Exercices";
  @override
  String exerciseCatalogSubtitle({required Object count}) => '$count mouvements';
  @override
  String get dataMigrationTitle => 'Migration de Données';
  @override
  String get dataMigrationSubtitle => 'Hevy / Strong / JSON';
  @override
  String get targetMusclesReady => "MUSCLES PRÊTS AUJOURD'HUI";
  @override
  String get recentWorkouts => 'SÉANCES RÉCENTES';
  @override
  String get noWorkoutsYet => 'Aucune séance enregistrée. Lancez votre première séance ci-dessus !';
  @override
  String get workoutSession => "Séance d'Entraînement";
  @override
  String exercisesCount({required Object count}) => '$count exercices';
  @override
  String get deleteSessionTooltip => 'Supprimer la séance';
  @override
  String get deleteSessionConfirmTitle => 'Supprimer la séance ?';
  @override
  String deleteSessionConfirmMessage({required Object title}) => '"$title" sera définitivement supprimée de vos séances récentes.';
  @override
  String get deleteSessionConfirmButton => 'Supprimer';
}

class _StringsAiCoachFr extends _StringsAiCoach {
  @override
  String get headerTitle => 'COACH PERSONNEL IA';
  @override
  String get modelBadge => 'ATLAS • Coach Biomécanique IA';
  @override
  String get liveActive => 'ATLAS Live Actif';
  @override
  String get liveVoiceToggle => 'Activer ATLAS Live';
  @override
  String get analyzingMovements => 'ATLAS analyse les exercices du catalogue...';
  @override
  String get youLabel => 'VOUS';
  @override
  String get liveCoachBadge => 'ATLAS • LIVE';
  @override
  String get flashCoachBadge => 'ATLAS • COACH IA';
  @override
  String get startAiWorkoutNow => 'Démarrer Cet Entraînement IA Maintenant';
  @override
  String setsRepsRest({required Object sets, required Object reps, required Object rest}) => '$sets séries × $reps reps • ${rest}s repos';
  @override
  String get form3dBadge => 'Forme 3D';
  @override
  String get formDemoBadge => 'Démo';
  @override
  String welcomeMessage({required Object chatModel, required Object liveModel}) =>
      "Bonjour ! Je suis ATLAS, votre Coach Personnel IA CommunityFitness. Sélectionnez les muscles à travailler ou demandez une alternative à la maison sans poids pour n'importe quel exercice du catalogue !";
  @override
  final _StringsAiCoachLiveBanner liveBanner = _StringsAiCoachLiveBannerFr();
  @override
  final _StringsAiCoachContextCard contextCard = _StringsAiCoachContextCardFr();
  @override
  final _StringsAiCoachPlannerCard plannerCard = _StringsAiCoachPlannerCardFr();
  @override
  final _StringsAiCoachAlternativesSheet alternativesSheet = _StringsAiCoachAlternativesSheetFr();
  @override
  final _StringsAiCoachChatInput chatInput = _StringsAiCoachChatInputFr();
  @override
  Map<String, String> get muscles => const {
    'Chest': 'Pectoraux',
    'Back': 'Dos',
    'Shoulders': 'Épaules',
    'Biceps': 'Biceps',
    'Triceps': 'Triceps',
    'Quadriceps': 'Quadriceps',
    'Quads': 'Quadriceps',
    'Hamstrings': 'Ischio-jambiers',
    'Glutes': 'Fessiers',
    'Calves': 'Mollets',
    'Abs / Core': 'Abdos / Gainage',
    'Core': 'Gainage',
    'Legs': 'Jambes',
    'Arms': 'Bras',
    'Full Body': 'Corps Entier',
  };
  @override
  Map<String, String> get equipment => const {
    'All': 'Tout',
    'Home / Bodyweight': 'Maison / Poids du Corps',
    'Dumbbells Only': 'Haltères Uniquement',
    'Bodyweight': 'Poids du Corps',
    'Barbell': 'Barre',
    'Dumbbell': 'Haltère',
    'Machine': 'Machine',
    'Cable': 'Poulie',
    'Kettlebell': 'Kettlebell',
  };
  @override
  Map<String, String> get constraints => const {
    'At Home / No Weights': 'À la Maison / Sans Poids',
    'Bodyweight Only': 'Poids du Corps Uniquement',
    'Dumbbells Only': 'Haltères Uniquement',
    'Joint Friendly': 'Doux pour les Articulations',
  };
  @override
  final _StringsAiCoachErrors errors = _StringsAiCoachErrorsFr();
}

class _StringsAiCoachLiveBannerFr extends _StringsAiCoachLiveBanner {
  @override
  String get listeningMic => 'ÉCOUTE DU MICRO — PARLEZ À ATLAS';
  @override
  String get connecting => 'CONNEXION À ATLAS LIVE...';
  @override
  String get listening => 'ÉCOUTE • PARLEZ OU APPUYEZ SUR UNE COMMANDE VOCALE';
  @override
  String get thinking => 'RÉFLEXION • ANALYSE BIOMÉCANIQUE EN TEMPS RÉEL';
  @override
  String get speaking => 'ATLAS PARLE • EN DIRECT';
  @override
  String get disconnected => 'DÉCONNECTÉ';
  @override
  String get defaultHint => "Demandez à votre Coach Live des conseils vocaux en temps réel ou des variantes d'exercices à domicile.";
  @override
  String get endSessionTooltip => 'Terminer la Session Vocale Live';
  @override
  String get quickChipChestAbs => 'Pectoraux et Abdos Maison (Sans Poids)';
  @override
  String get quickPromptChestAbs => 'Donne-moi un entraînement pectoraux et abdos à la maison sans poids';
  @override
  String get quickChipBackBiceps => 'Dos et Biceps à la Maison';
  @override
  String get quickPromptBackBiceps => 'Planifie un entraînement dos et biceps à la maison';
  @override
  String get quickChipLegsGlutes => 'Jambes et Fessiers Poids du Corps';
  @override
  String get quickPromptLegsGlutes => 'Crée une routine jambes et fessiers au poids du corps';
}

class _StringsAiCoachContextCardFr extends _StringsAiCoachContextCard {
  @override
  String targetExercise({required Object name}) => 'EXERCICE CIBLE : $name';
  @override
  String get subtitle => "Besoin d'une alternative pour vous entraîner à la maison ou sans matériel ? Choisissez une option :";
}

class _StringsAiCoachPlannerCardFr extends _StringsAiCoachPlannerCard {
  @override
  String get title => "QUELS MUSCLES VOULEZ-VOUS ENTRAÎNER AUJOURD'HUI ?";
  @override
  String get availableEquipment => 'ÉQUIPEMENT DISPONIBLE';
  @override
  String buildPlanButton({required Object muscles, required Object equipment}) => 'Créer Plan $muscles ($equipment)';
}

class _StringsAiCoachAlternativesSheetFr extends _StringsAiCoachAlternativesSheet {
  @override
  String title({required Object name}) => 'Alternatives IA pour $name';
  @override
  String get customHint => 'Note personnalisée (ex. à la maison avec chaise, douleur poignet)...';
}

class _StringsAiCoachChatInputFr extends _StringsAiCoachChatInput {
  @override
  String get listeningHint => 'Écoute de votre micro... Appuyez sur le bouton rouge pour envoyer';
  @override
  String get liveHint => 'Appuyez sur le micro pour parler ou écrivez à ATLAS Live...';
  @override
  String get defaultHint => 'Demandez des alternatives maison ou appuyez sur le micro...';
  @override
  String get sendTooltip => 'Envoyer le Message';
  @override
  String get stopMicTooltip => "Arrêter l'Enregistrement et Envoyer";
  @override
  String get startMicTooltip => 'Enregistrer la Voix (16kHz PCM)';
}

class _StringsAiCoachErrorsFr extends _StringsAiCoachErrors {
  @override
  String get loadAlternatives => 'Impossible de charger les alternatives pour le moment.';
  @override
  String get buildPlan => 'Impossible de créer le programme pour le moment.';
  @override
  String get coachReply => "Le coach n'a pas pu répondre pour le moment.";
}

class _StringsAnalyticsFr extends _StringsAnalytics {
  @override
  String get screenTitle => 'Équilibre et Récupération Musculaire';
  @override
  String get workoutsTitle => 'Séances';
  @override
  String get thisWeekSubtitle => 'Cette semaine';
  @override
  String get volumeTitle => 'Volume';
  @override
  String get bodyMapTitle => 'Carte Anatomique de Volume 3D';
  @override
  String get frontViewTab => 'Avant';
  @override
  String get backViewTab => 'Arrière';
  @override
  String get anteriorChainLabel => 'Chaîne Avant';
  @override
  String get posteriorChainLabel => 'Chaîne Arrière';
  @override
  String get recoveredStatus => 'Récupéré';
  @override
  String get recoveringStatus => 'En récupération';
  @override
  String get fatiguedStatus => 'Fatigué';
  @override
  String get zoneUnderMev => 'Sous MEV';
  @override
  String get zoneOptimalMav => 'MAV Optimal';
  @override
  String get zoneNearMrv => 'Proche MRV';
  @override
  String get zoneOverMrv => 'Sur MRV';
  @override
  String weeklySetsRange({required Object current, required Object min, required Object max}) => '$current / $min-$max séries';
  @override
  String recoveryPercent({required Object percent}) => '$percent% Récupération';
  @override
  String exploreMuscleExercises({required Object muscle}) => 'Explorer les Exercices ($muscle)';
  @override
  String get muscleRecoverySectionTitle => 'Récupération Musculaire';
  @override
  String readyCountBadge({required Object ready, required Object total}) => '$ready/$total Prêts';
  @override
  String setsMevSummary({required Object sets, required Object mavMax, required Object mev}) => '$sets/$mavMax séries · MEV $mev';
  @override
  String get estimated1rmSectionTitle => 'Records 1RM Estimés';
  @override
  String get noPrsYet => 'Complétez des séries avec poids pour débloquer votre 1RM.';
  @override
  String bestSetSubtitle({required Object weight, required Object reps}) => 'Meilleur : ${weight}kg × $reps';
}

class _StringsWorkoutFr extends _StringsWorkout {
  @override
  String get finishButton => 'Terminer';
  @override
  String get durationLabel => 'Durée';
  @override
  String get completedSetsLabel => 'Séries Complétées';
  @override
  String get exercisesLabel => 'Exercices';
  @override
  String get addExerciseButton => 'Ajouter un Exercice';
  @override
  String get machineBusySwapPill => 'Machine Occupée · Changer';
  @override
  String get machineBusyModalTitle => "Machine Occupée (Changer d'Exercice)";
  @override
  String ghostPaceCompare({required Object live, required Object target}) => 'Vous : $live kg · Rythme Ghost : $target kg';
  @override
  String ghostAheadBadge({required Object delta}) => "+$delta kg d'Avance";
  @override
  String ghostBehindBadge({required Object delta}) => '$delta kg de Retard';
  @override
  String get ghostOnPaceBadge => 'Dans le Rythme';
  @override
  String get anatomicalCardHeader => "CARTE ANATOMIQUE D'ENTRAÎNEMENT";
  @override
  String ghostVerdictAhead({required Object delta}) => "Verdict Ghost : +$delta kg d'Avance";
  @override
  String ghostVerdictBehind({required Object delta}) => 'Verdict Ghost : $delta kg de Retard';
  @override
  String get ghostVerdictOnPace => 'Verdict Ghost : Dans le Rythme';
  @override
  String get ghostVerdictCompleted => 'Verdict Ghost : Terminé';
  @override
  String get muscleActivationSectionTitle => "CARTE D'ACTIVATION MUSCULAIRE";
  @override
  String get copyShareCardButton => 'Copier la Carte';
  @override
  String get doneButton => 'Terminé';
  @override
  String get cardCopiedSnackbar => 'Carte anatomique copiée dans le presse-papiers !';
}

class _StringsHybridAiFr extends _StringsHybridAi {
  @override
  String get aiCoachToggleChip => 'NPU Hybride';
  @override
  String get routerTitle => 'Routeur IA Hybride ATLAS';
  @override
  String npuStatusPrefix({required Object status}) => 'NPU AICore : $status';
  @override
  String get statusOnDeviceReady => "Prêt sur l'Appareil";
  @override
  String get statusDownloadable => 'Téléchargeable';
  @override
  String get statusDownloading => 'Téléchargement du Modèle';
  @override
  String get statusCloudFallback => 'Secours Cloud';
  @override
  String get sourceOnDeviceNano => "SUR L'APPAREIL · Gemini Nano";
  @override
  String get sourceOnDeviceApple => "SUR L'APPAREIL · Apple Intelligence";
  @override
  String get sourceOnDeviceChrome => "SUR L'APPAREIL · Chrome Gemini Nano";
  @override
  String get sourceOnDeviceShort => "SUR L'APPAREIL";
  @override
  String sourceInCloud({required Object model}) => 'DANS LE CLOUD · $model';
  @override
  String get sourceInCloudShort => 'DANS LE CLOUD';
  @override
  String get sourceOfflineEngine => 'MOTEUR HORS LIGNE';
  @override
  String get ramWarmedUp => 'RAM Préchauffée';
  @override
  String get downloadModelButton => 'Télécharger le Modèle Local';
  @override
  String dotpromptBadge({required Object templateId}) => 'Dotprompt · $templateId';
  @override
  String remoteConfigOnlyBadge({required Object templateId}) => 'Remote Config Seul · $templateId';
  @override
  String get modeSectionTitle => "Politique d'Exécution (Firebase AI Logic InferenceMode)";
  @override
  String get modeSectionSubtitle => 'Acheminez les requêtes entre Gemini Nano local (AICore) et Cloud Gemini.';
  @override
  String get modePreferOnDevice => "Préférer sur l'Appareil";
  @override
  String get modeOnlyOnDevice => "Uniquement sur l'Appareil";
  @override
  String get modePreferInCloud => 'Préférer dans le Cloud';
  @override
  String get modeOnlyInCloud => 'Uniquement dans le Cloud';
  @override
  String get loggerTitle => 'Autorégulateur de Séries Hors Ligne';
  @override
  String get loggerSubtitle => "Enregistrez vos séries en langage naturel ou scannez l'équipement sans latence cloud.";
  @override
  String get presetHeavyBenchChip => 'Développé Couché Lourd (100kg x 6 @ RPE 9.5)';
  @override
  String get presetFastSquatChip => 'Squat Rapide (120kg x 8 @ RPE 7.0)';
  @override
  String get inputHint => 'ex. Développé Couché Barre 100kg x 6 @ RPE 9.5';
  @override
  String get analyzeSetButton => 'Analyser la Série';
  @override
  String get scanEquipmentButton => "Scanner l'Équipement";
  @override
  String get loadLabel => 'CHARGE';
  @override
  String get repsLabel => 'REPS';
  @override
  String get rpeLabel => 'RPE';
  @override
  String get fatigueAlertBadge => 'Alerte Fatigue SNC';
  @override
  String get optimalVelocityBadge => 'Vitesse Optimale';
  @override
  String get visionCardTitle => "Scan Multimodal d'Équipement (Image + Prompt)";
  @override
  String get activeWorkoutSectionTitle => 'AUTORÉGULATION DE SÉRIE NPU HYBRIDE';
  @override
  String get rpe7Chip => 'RPE 7 · +2.5kg';
  @override
  String get rpe85Chip => 'RPE 8.5 · Maintenir';
  @override
  String get rpe95Chip => 'RPE 9.5 · -5% Charge';
  @override
  String get fatigueAlertBannerBadge => 'ALERTE FATIGUE';
  @override
  String recHighFatigueWithWeight({required Object rpe, required Object weight}) =>
      'Forte fatigue du SNC détectée (RPE $rpe). Réduisez la charge à ${weight}kg et reposez-vous 180s avant la prochaine série.';
  @override
  String recHighFatigueNoWeight({required Object rpe}) =>
      'Forte fatigue du SNC détectée (RPE $rpe). Réduisez la charge de 5% et reposez-vous 180s avant la prochaine série.';
  @override
  String recNearFailureWithWeight({required Object rpe, required Object weight}) =>
      "Proche de l'échec musculaire (RPE $rpe). Maintenez ${weight}kg, concentrez-vous sur la vitesse de barre et reposez-vous 150-180s.";
  @override
  String recNearFailureNoWeight({required Object rpe}) =>
      "Proche de l'échec musculaire (RPE $rpe). Maintenez la charge actuelle et reposez-vous 150-180s.";
  @override
  String recProgressiveOverload({required Object rpe, required Object weight, required Object reps}) =>
      'Excellente vitesse de barre (RPE $rpe). Appliquez une surcharge progressive : passez à ${weight}kg pour $reps répétitions.';
  @override
  String recOptimalWithWeight({required Object rpe, required Object weight, required Object reps}) =>
      "Zone d'hypertrophie optimale (RPE $rpe). Gardez ${weight}kg pour $reps répétitions avec 90-120s de repos.";
  @override
  String recOptimalNoWeight({required Object rpe, required Object reps}) =>
      "Stimulus d'entraînement optimal (RPE $rpe). Maintenez la charge pour $reps répétitions avec 90-120s de repos.";
  @override
  String errorOnlyOnDeviceUnavailable({required Object status}) =>
      "Le mode Uniquement sur l'Appareil nécessite les poids NPU locaux (statut actuel : $status).";
}

// -----------------------------------------------------------------------------
// Português (pt)
// -----------------------------------------------------------------------------

class _TranslationsPt extends Translations {
  @override
  final _StringsCommon common = _StringsCommonPt();
  @override
  final _StringsDashboard dashboard = _StringsDashboardPt();
  @override
  final _StringsAiCoach aiCoach = _StringsAiCoachPt();
  @override
  final _StringsAnalytics analytics = _StringsAnalyticsPt();
  @override
  final _StringsWorkout workout = _StringsWorkoutPt();
  @override
  final _StringsHybridAi hybridAi = _StringsHybridAiPt();
}

class _StringsCommonPt extends _StringsCommon {
  @override
  String get appName => 'COMMUNITY FITNESS';
  @override
  String get language => 'Idioma';
  @override
  String get selectLanguage => 'Selecionar Idioma';
  @override
  String get cancel => 'Cancelar';
  @override
  String get close => 'Fechar';
  @override
  Map<String, String> get languages => const {'es': 'Español', 'en': 'English', 'ca': 'Català', 'fr': 'Français', 'pt': 'Português'};
}

class _StringsDashboardPt extends _StringsDashboard {
  @override
  String get aiCoachTooltip => 'ATLAS • Personal Trainer IA';
  @override
  String get dataManagementTooltip => 'Gestão de Dados';
  @override
  String get muscleAnalyticsTooltip => 'Análise Muscular';
  @override
  String get languageTooltip => 'Mudar Idioma';
  @override
  String get readyToTrain => 'PRONTO PARA TREINAR';
  @override
  String workoutsThisWeek({required Object count}) => '$count treinos esta semana';
  @override
  String get freestyleTraining => 'Treino Livre';
  @override
  String exercisesPlanned({required Object count}) => '$count exercícios planeados';
  @override
  String get buildOnTheFly => 'Crie a sua sessão na hora';
  @override
  String get totalSets => 'SÉRIES TOTAIS';
  @override
  String get movements => 'MOVIMENTOS';
  @override
  String get targetIntensity => 'INTENSIDADE ALVO';
  @override
  String get startRoutine => 'Iniciar Rotina';
  @override
  String get startFreestyle => 'Treino Livre';
  @override
  String get exploreAndManage => 'EXPLORAR E GERIR';
  @override
  String get routinesTitle => 'Rotinas';
  @override
  String routinesSubtitle({required Object count}) => '$count divisões guardadas';
  @override
  String get muscleRecoveryTitle => 'Recuperação Muscular';
  @override
  String muscleRecoverySubtitle({required Object count}) => '$count músculos prontos';
  @override
  String get exerciseCatalogTitle => 'Catálogo de Exercícios';
  @override
  String exerciseCatalogSubtitle({required Object count}) => '$count movimentos';
  @override
  String get dataMigrationTitle => 'Migração de Dados';
  @override
  String get dataMigrationSubtitle => 'Hevy / Strong / JSON';
  @override
  String get targetMusclesReady => 'MÚSCULOS PRONTOS HOJE';
  @override
  String get recentWorkouts => 'TREINOS RECENTES';
  @override
  String get noWorkoutsYet => 'Ainda não há treinos registados. Comece a sua primeira sessão acima!';
  @override
  String get workoutSession => 'Sessão de Treino';
  @override
  String exercisesCount({required Object count}) => '$count exercícios';
  @override
  String get deleteSessionTooltip => 'Eliminar sessão';
  @override
  String get deleteSessionConfirmTitle => 'Eliminar sessão de treino?';
  @override
  String deleteSessionConfirmMessage({required Object title}) => '"$title" será removida permanentemente dos seus treinos recentes.';
  @override
  String get deleteSessionConfirmButton => 'Eliminar';
}

class _StringsAiCoachPt extends _StringsAiCoach {
  @override
  String get headerTitle => 'PERSONAL TRAINER IA';
  @override
  String get modelBadge => 'ATLAS • Treinador Biomecânico IA';
  @override
  String get liveActive => 'ATLAS Ao Vivo Ativo';
  @override
  String get liveVoiceToggle => 'Ativar ATLAS Live';
  @override
  String get analyzingMovements => 'O ATLAS está a analisar movimentos do catálogo...';
  @override
  String get youLabel => 'VOCÊ';
  @override
  String get liveCoachBadge => 'ATLAS • AO VIVO';
  @override
  String get flashCoachBadge => 'ATLAS • COACH IA';
  @override
  String get startAiWorkoutNow => 'Iniciar Este Treino IA Agora';
  @override
  String setsRepsRest({required Object sets, required Object reps, required Object rest}) => '$sets séries × $reps reps • ${rest}s descanso';
  @override
  String get form3dBadge => 'Forma 3D';
  @override
  String get formDemoBadge => 'Demo';
  @override
  String welcomeMessage({required Object chatModel, required Object liveModel}) =>
      'Olá! Sou o ATLAS, o seu Personal Trainer IA da CommunityFitness. Selecione os músculos que quer treinar ou peça uma alternativa em casa sem pesos para qualquer exercício do catálogo!';
  @override
  final _StringsAiCoachLiveBanner liveBanner = _StringsAiCoachLiveBannerPt();
  @override
  final _StringsAiCoachContextCard contextCard = _StringsAiCoachContextCardPt();
  @override
  final _StringsAiCoachPlannerCard plannerCard = _StringsAiCoachPlannerCardPt();
  @override
  final _StringsAiCoachAlternativesSheet alternativesSheet = _StringsAiCoachAlternativesSheetPt();
  @override
  final _StringsAiCoachChatInput chatInput = _StringsAiCoachChatInputPt();
  @override
  Map<String, String> get muscles => const {
    'Chest': 'Peito',
    'Back': 'Costas',
    'Shoulders': 'Ombros',
    'Biceps': 'Bíceps',
    'Triceps': 'Tríceps',
    'Quadriceps': 'Quadríceps',
    'Quads': 'Quadríceps',
    'Hamstrings': 'Isquiotibiais',
    'Glutes': 'Glúteos',
    'Calves': 'Gémeos',
    'Abs / Core': 'Abdómen / Core',
    'Core': 'Core',
    'Legs': 'Pernas',
    'Arms': 'Braços',
    'Full Body': 'Corpo Inteiro',
  };
  @override
  Map<String, String> get equipment => const {
    'All': 'Tudo',
    'Home / Bodyweight': 'Em Casa / Peso Corporal',
    'Dumbbells Only': 'Apenas Halteres',
    'Bodyweight': 'Peso Corporal',
    'Barbell': 'Barra',
    'Dumbbell': 'Haltere',
    'Machine': 'Máquina',
    'Cable': 'Polia',
    'Kettlebell': 'Kettlebell',
  };
  @override
  Map<String, String> get constraints => const {
    'At Home / No Weights': 'Em Casa / Sem Pesos',
    'Bodyweight Only': 'Apenas Peso Corporal',
    'Dumbbells Only': 'Apenas Halteres',
    'Joint Friendly': 'Proteção Articular',
  };
  @override
  final _StringsAiCoachErrors errors = _StringsAiCoachErrorsPt();
}

class _StringsAiCoachLiveBannerPt extends _StringsAiCoachLiveBanner {
  @override
  String get listeningMic => 'A OUVIR O SEU MICROFONE — FALE COM O ATLAS';
  @override
  String get connecting => 'A LIGAR AO ATLAS AO VIVO...';
  @override
  String get listening => 'A OUVIR • FALE OU TOQUE NUM COMANDO DE VOZ';
  @override
  String get thinking => 'A PENSAR • RACIOCÍNIO BIOMECÂNICO EM TEMPO REAL';
  @override
  String get speaking => 'ATLAS ESTÁ A FALAR • AO VIVO';
  @override
  String get disconnected => 'DESLIGADO';
  @override
  String get defaultHint => 'Peça ao seu Personal Trainer Ao Vivo dicas de voz em tempo real ou trocas de exercícios em casa.';
  @override
  String get endSessionTooltip => 'Terminar Sessão de Voz Ao Vivo';
  @override
  String get quickChipChestAbs => 'Peito e Abdómen em Casa (Sem Pesos)';
  @override
  String get quickPromptChestAbs => 'Dá-me um treino de peito e abdominais em casa sem pesos';
  @override
  String get quickChipBackBiceps => 'Costas e Bíceps em Casa';
  @override
  String get quickPromptBackBiceps => 'Planeia um treino de costas e bíceps em casa';
  @override
  String get quickChipLegsGlutes => 'Pernas e Glúteos Peso Corporal';
  @override
  String get quickPromptLegsGlutes => 'Cria uma rotina de pernas e glúteos com peso corporal';
}

class _StringsAiCoachContextCardPt extends _StringsAiCoachContextCard {
  @override
  String targetExercise({required Object name}) => 'EXERCÍCIO ALVO: $name';
  @override
  String get subtitle => 'Precisa de uma alternativa porque treina em casa ou sem equipamento? Toque numa opção:';
}

class _StringsAiCoachPlannerCardPt extends _StringsAiCoachPlannerCard {
  @override
  String get title => 'QUE MÚSCULOS QUER TREINAR HOJE?';
  @override
  String get availableEquipment => 'EQUIPAMENTO DISPONÍVEL';
  @override
  String buildPlanButton({required Object muscles, required Object equipment}) => 'Criar Plano de $muscles ($equipment)';
}

class _StringsAiCoachAlternativesSheetPt extends _StringsAiCoachAlternativesSheet {
  @override
  String title({required Object name}) => 'Alternativas IA para $name';
  @override
  String get customHint => 'Nota personalizada (ex. em casa com cadeira, dor no pulso)...';
}

class _StringsAiCoachChatInputPt extends _StringsAiCoachChatInput {
  @override
  String get listeningHint => 'A ouvir o seu microfone... Toque no botão vermelho para enviar';
  @override
  String get liveHint => 'Toque no mic para falar ou escreva para o ATLAS Live...';
  @override
  String get defaultHint => 'Peça alternativas em casa ou toque no mic para falar...';
  @override
  String get sendTooltip => 'Enviar Mensagem';
  @override
  String get stopMicTooltip => 'Parar Gravação e Enviar Voz';
  @override
  String get startMicTooltip => 'Gravar Voz (16kHz PCM)';
}

class _StringsAiCoachErrorsPt extends _StringsAiCoachErrors {
  @override
  String get loadAlternatives => 'Não foi possível carregar as alternativas neste momento.';
  @override
  String get buildPlan => 'Não foi possível criar o plano de treino neste momento.';
  @override
  String get coachReply => 'O treinador não conseguiu responder neste momento.';
}

class _StringsAnalyticsPt extends _StringsAnalytics {
  @override
  String get screenTitle => 'Equilíbrio e Recuperação Muscular';
  @override
  String get workoutsTitle => 'Treinos';
  @override
  String get thisWeekSubtitle => 'Esta semana';
  @override
  String get volumeTitle => 'Volume';
  @override
  String get bodyMapTitle => 'Mapa Anatómico de Volume 3D';
  @override
  String get frontViewTab => 'Frontal';
  @override
  String get backViewTab => 'Posterior';
  @override
  String get anteriorChainLabel => 'Cadeia Frontal';
  @override
  String get posteriorChainLabel => 'Cadeia Posterior';
  @override
  String get recoveredStatus => 'Recuperado';
  @override
  String get recoveringStatus => 'A recuperar';
  @override
  String get fatiguedStatus => 'Fatigado';
  @override
  String get zoneUnderMev => 'Abaixo MEV';
  @override
  String get zoneOptimalMav => 'MAV Ótimo';
  @override
  String get zoneNearMrv => 'Perto de MRV';
  @override
  String get zoneOverMrv => 'Acima MRV';
  @override
  String weeklySetsRange({required Object current, required Object min, required Object max}) => '$current / $min-$max séries';
  @override
  String recoveryPercent({required Object percent}) => '$percent% Recuperação';
  @override
  String exploreMuscleExercises({required Object muscle}) => 'Explorar Exercícios de $muscle';
  @override
  String get muscleRecoverySectionTitle => 'Recuperação Muscular';
  @override
  String readyCountBadge({required Object ready, required Object total}) => '$ready/$total Prontos';
  @override
  String setsMevSummary({required Object sets, required Object mavMax, required Object mev}) => '$sets/$mavMax séries · MEV $mev';
  @override
  String get estimated1rmSectionTitle => 'Recordes de 1RM Estimado';
  @override
  String get noPrsYet => 'Complete séries com peso para desbloquear o seu 1RM.';
  @override
  String bestSetSubtitle({required Object weight, required Object reps}) => 'Melhor: ${weight}kg × $reps';
}

class _StringsWorkoutPt extends _StringsWorkout {
  @override
  String get finishButton => 'Terminar';
  @override
  String get durationLabel => 'Duração';
  @override
  String get completedSetsLabel => 'Séries Concluídas';
  @override
  String get exercisesLabel => 'Exercícios';
  @override
  String get addExerciseButton => 'Adicionar Exercício';
  @override
  String get machineBusySwapPill => 'Máquina Ocupada · Trocar';
  @override
  String get machineBusyModalTitle => 'Máquina Ocupada (Trocar Exercício)';
  @override
  String ghostPaceCompare({required Object live, required Object target}) => 'Você: $live kg · Ritmo Ghost: $target kg';
  @override
  String ghostAheadBadge({required Object delta}) => '+$delta kg à Frente';
  @override
  String ghostBehindBadge({required Object delta}) => '$delta kg Atrás';
  @override
  String get ghostOnPaceBadge => 'No Ritmo';
  @override
  String get anatomicalCardHeader => 'CARTÃO ANATÓMICO DE TREINO';
  @override
  String ghostVerdictAhead({required Object delta}) => 'Veredito Ghost: +$delta kg à Frente';
  @override
  String ghostVerdictBehind({required Object delta}) => 'Veredito Ghost: $delta kg Atrás';
  @override
  String get ghostVerdictOnPace => 'Veredito Ghost: No Ritmo';
  @override
  String get ghostVerdictCompleted => 'Veredito Ghost: Concluído';
  @override
  String get muscleActivationSectionTitle => 'MAPA DE ATIVAÇÃO MUSCULAR';
  @override
  String get copyShareCardButton => 'Copiar Cartão';
  @override
  String get doneButton => 'Concluído';
  @override
  String get cardCopiedSnackbar => 'Cartão anatómico copiado para a área de transferência!';
}

class _StringsHybridAiPt extends _StringsHybridAi {
  @override
  String get aiCoachToggleChip => 'NPU Híbrido';
  @override
  String get routerTitle => 'Router IA Híbrido ATLAS';
  @override
  String npuStatusPrefix({required Object status}) => 'NPU AICore: $status';
  @override
  String get statusOnDeviceReady => 'Pronto no Dispositivo';
  @override
  String get statusDownloadable => 'Transferível';
  @override
  String get statusDownloading => 'A Transferir Modelo';
  @override
  String get statusCloudFallback => 'Alternativa na Nuvem';
  @override
  String get sourceOnDeviceNano => 'NO DISPOSITIVO · Gemini Nano';
  @override
  String get sourceOnDeviceApple => 'NO DISPOSITIVO · Apple Intelligence';
  @override
  String get sourceOnDeviceChrome => 'NO DISPOSITIVO · Chrome Gemini Nano';
  @override
  String get sourceOnDeviceShort => 'NO DISPOSITIVO';
  @override
  String sourceInCloud({required Object model}) => 'NA NUVEM · $model';
  @override
  String get sourceInCloudShort => 'NA NUVEM';
  @override
  String get sourceOfflineEngine => 'MOTOR OFFLINE';
  @override
  String get ramWarmedUp => 'RAM Pré-aquecida';
  @override
  String get downloadModelButton => 'Transferir Modelo Local';
  @override
  String dotpromptBadge({required Object templateId}) => 'Dotprompt · $templateId';
  @override
  String remoteConfigOnlyBadge({required Object templateId}) => 'Apenas Remote Config · $templateId';
  @override
  String get modeSectionTitle => 'Política de Execução (Firebase AI Logic InferenceMode)';
  @override
  String get modeSectionSubtitle => 'Encaminhe pedidos entre o Gemini Nano local (AICore) e o Cloud Gemini.';
  @override
  String get modePreferOnDevice => 'Preferir no Dispositivo';
  @override
  String get modeOnlyOnDevice => 'Apenas no Dispositivo';
  @override
  String get modePreferInCloud => 'Preferir na Nuvem';
  @override
  String get modeOnlyInCloud => 'Apenas na Nuvem';
  @override
  String get loggerTitle => 'Autorregulador de Séries Offline';
  @override
  String get loggerSubtitle => 'Registe séries em linguagem natural ou digitalize equipamento sem latência na nuvem.';
  @override
  String get presetHeavyBenchChip => 'Supino Pesado (100kg x 6 @ RPE 9.5)';
  @override
  String get presetFastSquatChip => 'Agachamento Rápido (120kg x 8 @ RPE 7.0)';
  @override
  String get inputHint => 'ex. Supino Reto com Barra 100kg x 6 @ RPE 9.5';
  @override
  String get analyzeSetButton => 'Analisar Série';
  @override
  String get scanEquipmentButton => 'Digitalizar Equipamento';
  @override
  String get loadLabel => 'CARGA';
  @override
  String get repsLabel => 'REPS';
  @override
  String get rpeLabel => 'RPE';
  @override
  String get fatigueAlertBadge => 'Alerta de Fadiga SNC';
  @override
  String get optimalVelocityBadge => 'Velocidade Ótima';
  @override
  String get visionCardTitle => 'Digitalização Multimodal de Equipamento (Imagem + Prompt)';
  @override
  String get activeWorkoutSectionTitle => 'AUTORREGULAÇÃO DE SÉRIE NPU HÍBRIDO';
  @override
  String get rpe7Chip => 'RPE 7 · +2.5kg';
  @override
  String get rpe85Chip => 'RPE 8.5 · Manter';
  @override
  String get rpe95Chip => 'RPE 9.5 · -5% Carga';
  @override
  String get fatigueAlertBannerBadge => 'ALERTA DE FADIGA';
  @override
  String recHighFatigueWithWeight({required Object rpe, required Object weight}) =>
      'Fadiga elevada do SNC detetada (RPE $rpe). Reduza a carga para ${weight}kg e descanse 180s antes da próxima série.';
  @override
  String recHighFatigueNoWeight({required Object rpe}) =>
      'Fadiga elevada do SNC detetada (RPE $rpe). Reduza a carga em 5% e descanse 180s antes da próxima série.';
  @override
  String recNearFailureWithWeight({required Object rpe, required Object weight}) =>
      'Perto da falha muscular (RPE $rpe). Mantenha ${weight}kg, foque na velocidade da barra e descanse 150-180s.';
  @override
  String recNearFailureNoWeight({required Object rpe}) =>
      'Perto da falha muscular (RPE $rpe). Mantenha a carga atual e descanse 150-180s.';
  @override
  String recProgressiveOverload({required Object rpe, required Object weight, required Object reps}) =>
      'Forte velocidade da barra (RPE $rpe). Aplique sobrecarga progressiva: aumente para ${weight}kg para $reps repetições.';
  @override
  String recOptimalWithWeight({required Object rpe, required Object weight, required Object reps}) =>
      'Zona ótima de hipertrofia (RPE $rpe). Mantenha ${weight}kg para $reps repetições com 90-120s de descanso.';
  @override
  String recOptimalNoWeight({required Object rpe, required Object reps}) =>
      'Estímulo de treino ótimo (RPE $rpe). Mantenha a carga para $reps repetições com 90-120s de descanso.';
  @override
  String errorOnlyOnDeviceUnavailable({required Object status}) =>
      'O modo Apenas no Dispositivo requer pesos NPU locais (estado atual: $status).';
}
