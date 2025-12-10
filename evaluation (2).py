"""
Model exported as python.
Name : модель
Group :
With QGIS : 34201
"""

from typing import Any, Optional
import os

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingUtils,
    QgsCoordinateReferenceSystem,
    QgsProject
)
from qgis import processing


class модель(QgsProcessingAlgorithm):

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        self.addParameter(QgsProcessingParameterVectorLayer('complited', 'Complited', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('contour', 'Contour', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('task', 'Task', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))

        self.addParameter(
            QgsProcessingParameterField(
                'FIELD_FACT',
                'Поле с фактическим значением (из Complited)',
                parentLayerParameterName='complited',
                type=QgsProcessingParameterField.Numeric,
                defaultValue='current2'
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                'FIELD_PLAN',
                'Поле с плановым значением (из Task)',
                parentLayerParameterName='task',
                type=QgsProcessingParameterField.Numeric,
                defaultValue='target'
            )
        )

        # Параметры расстояний буфера
        self.addParameter(
            QgsProcessingParameterNumber(
                'BUFFER_CONTOUR_DIST',
                'Расстояние буфера у контура (в единицах CRS)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0001,
                minValue=0.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'BUFFER_TRANSITION_DIST',
                'Расстояние буфера у переходов (в единицах CRS)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5e-06,
                minValue=0.0
            )
        )

        # Outputs
        sinks = [
            ('Buffertransition', 'BufferTransition', QgsProcessing.TypeVectorPolygon),
            ('Buffercontour', 'BufferContour', QgsProcessing.TypeVectorPolygon),
            ('Contourfield', 'ContourField', QgsProcessing.TypeVectorAnyGeometry),
            ('Line', 'Line', QgsProcessing.TypeVectorAnyGeometry),
            ('Elsemistake', 'ElseMistake', QgsProcessing.TypeVectorAnyGeometry),
            ('Unitedtask', 'UnitedTask', QgsProcessing.TypeVectorAnyGeometry),
            ('Bad', 'bad', QgsProcessing.TypeVectorAnyGeometry),
            ('Good', 'good', QgsProcessing.TypeVectorAnyGeometry),
            ('Complited_polygons', 'Complited_polygons', QgsProcessing.TypeVectorAnyGeometry),
            ('Transitionmistake', 'TransitionMistake', QgsProcessing.TypeVectorAnyGeometry),
            ('Percent_seed', 'percent_seed', QgsProcessing.TypeVectorAnyGeometry),
            ('Complited_fixed', 'Complited_fixed', QgsProcessing.TypeVectorAnyGeometry),
            ('Contourmistake', 'ContourMistake', QgsProcessing.TypeVectorAnyGeometry),
            ('Complited_with_plan', 'Complited_with_plan', QgsProcessing.TypeVectorAnyGeometry),
            ('Contourfieldline', 'ContourFieldLine', QgsProcessing.TypeVectorLine),
            ('Contourline', 'ContourLine', QgsProcessing.TypeVectorLine),
        ]
        for name, desc, typ in sinks:
            self.addParameter(QgsProcessingParameterFeatureSink(
                name, desc, type=typ, createByDefault=True,
                defaultValue=QgsProcessing.TEMPORARY_OUTPUT if name == 'Bad' else None
            ))

    def processAlgorithm(self, parameters: dict[str, Any], context: QgsProcessingContext, model_feedback: QgsProcessingFeedback) -> dict[str, Any]:
        # Обновлено: всего 22 шага
        feedback = QgsProcessingMultiStepFeedback(22, model_feedback)
        results = {}
        outputs = {}

        step = 1

        # 1. ContourField — поле по заданию
        alg_params = {'INPUT': parameters['contour'], 'OVERLAY': parameters['task'], 'OUTPUT': parameters['Contourfield']}
        outputs['Contourfield'] = processing.run('native:clip', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Contourfield'] = outputs['Contourfield']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 2. ContourFieldLine
        alg_params = {'INPUT': outputs['Contourfield']['OUTPUT'], 'OUTPUT': parameters['Contourfieldline']}
        outputs['Contourlines'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Contourfieldline'] = outputs['Contourlines']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 3. UnitedTask
        alg_params = {'FIELD': ['1_seed', '2_fert'], 'INPUT': parameters['task'], 'SEPARATE_DISJOINT': False, 'OUTPUT': parameters['Unitedtask']}
        outputs['Unitedtask'] = processing.run('native:dissolve', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Unitedtask'] = outputs['Unitedtask']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 4. Complited_fixed
        alg_params = {'INPUT': parameters['complited'], 'METHOD': 1, 'OUTPUT': parameters['Complited_fixed']}
        outputs['Complited_fixed'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Complited_fixed'] = outputs['Complited_fixed']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 5. Complited_polygons (только полигоны)
        alg_params = {'EXPRESSION': "geom_to_wkt(@geometry) ILIKE '%POLYGON%'", 'INPUT': outputs['Complited_fixed']['OUTPUT'], 'OUTPUT': parameters['Complited_polygons']}
        outputs['Complited_polygons'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Complited_polygons'] = outputs['Complited_polygons']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 6. Complited_outside — работа ВНЕ поля
        alg_params = {'INPUT': outputs['Complited_polygons']['OUTPUT'], 'OVERLAY': outputs['Contourfield']['OUTPUT'], 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT}
        outputs['Complited_outside_raw'] = processing.run('native:difference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        alg_params = {
            'INPUT': outputs['Complited_outside_raw']['OUTPUT'],
            'FIELD_NAME': 'area_ha',
            'FIELD_TYPE': 0, 'FIELD_LENGTH': 12, 'FIELD_PRECISION': 4,
            'FORMULA': '$area / 10000',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Complited_outside'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Complited_outside'] = outputs['Complited_outside']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 7. BufferContour — с пользовательским расстоянием
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['BUFFER_CONTOUR_DIST'],
            'END_CAP_STYLE': 0,
            'INPUT': outputs['Contourlines']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': parameters['Buffercontour']
        }
        outputs['Buffercontour'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Buffercontour'] = outputs['Buffercontour']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 8. ContourLine (from UnitedTask)
        alg_params = {'INPUT': outputs['Unitedtask']['OUTPUT'], 'OUTPUT': parameters['Contourline']}
        outputs['Tasklines'] = processing.run('native:polygonstolines', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Contourline'] = outputs['Tasklines']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 9. Add area_ha to Complited_polygons
        alg_params = {
            'INPUT': outputs['Complited_polygons']['OUTPUT'],
            'FIELD_NAME': 'area_ha', 'FIELD_TYPE': 0, 'FIELD_LENGTH': 10, 'FIELD_PRECISION': 3,
            'FORMULA': '$area / 10000',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Complited_with_area'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 10. Complited_with_plan (join with task)
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['Complited_with_area']['OUTPUT'],
            'JOIN': parameters['task'],
            'JOIN_FIELDS': [], 'METHOD': 0, 'PREDICATE': [0], 'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Complited_with_plan'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 11. TransitionLines
        alg_params = {'GRID_SIZE': None, 'INPUT': outputs['Tasklines']['OUTPUT'], 'OVERLAY': outputs['Contourlines']['OUTPUT'], 'OUTPUT': parameters['Line']}
        outputs['Transitionlines'] = processing.run('native:difference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Line'] = outputs['Transitionlines']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 12. Percent field
        alg_params = {
            'INPUT': outputs['Complited_with_plan']['OUTPUT'],
            'FIELD_NAME': 'percent', 'FIELD_TYPE': 0, 'FIELD_LENGTH': 10, 'FIELD_PRECISION': 3,
            'FORMULA': f'"{parameters["FIELD_FACT"]}" / "{parameters["FIELD_PLAN"]}"',
            'OUTPUT': parameters['Percent_seed']
        }
        outputs['Percent'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Percent_seed'] = outputs['Percent']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 13. BufferTransition — с пользовательским расстоянием
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': parameters['BUFFER_TRANSITION_DIST'],
            'END_CAP_STYLE': 0,
            'INPUT': outputs['Transitionlines']['OUTPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'SEPARATE_DISJOINT': False,
            'OUTPUT': parameters['Buffertransition']
        }
        outputs['Buffertransition'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Buffertransition'] = outputs['Buffertransition']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 14–17. Категории по проценту
        categories = [
            ('Good', '"percent" >= 0.95 AND "percent" <= 1.05'),
            ('Under', '"percent" < 0.95'),
            ('Over', '"percent" > 1.05 AND "percent" < 2.0'),
            ('Over2', '"percent" >= 2.0')
        ]
        for name, expr in categories:
            alg_params = {'EXPRESSION': expr, 'INPUT': outputs['Percent']['OUTPUT'], 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT}
            out = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            results[name] = out['OUTPUT']
            feedback.setCurrentStep(step); step += 1
            if feedback.isCanceled(): return {}

        # 18. Bad = Under + Over + Over2
        alg_params = {'LAYERS': [results['Under'], results['Over'], results['Over2']], 'OUTPUT': parameters['Bad']}
        outputs['Bad'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Bad'] = outputs['Bad']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 19. TransitionMistake
        alg_params = {'INPUT': results['Bad'], 'INTERSECT': results['Buffertransition'], 'PREDICATE': [0, 4, 7], 'OUTPUT': parameters['Transitionmistake']}
        outputs['Transitionmistake'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Transitionmistake'] = outputs['Transitionmistake']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 20. ContourMistake
        alg_params = {
            'INPUT': results['Bad'], 'INPUT_FIELDS': [], 'OVERLAY': results['Buffercontour'], 'OVERLAY_FIELDS': [],
            'OVERLAY_FIELDS_PREFIX': '', 'OUTPUT': parameters['Contourmistake']
        }
        outputs['Contourmistake'] = processing.run('native:intersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Contourmistake'] = outputs['Contourmistake']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 21. Union mistakes
        alg_params = {'INPUT': results['Transitionmistake'], 'OVERLAY': results['Contourmistake'], 'OVERLAY_FIELDS_PREFIX': '', 'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT}
        outputs['Union_mistakes'] = processing.run('native:union', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # 22. Elsemistake = Bad − (Transition ∪ Contour)
        alg_params = {'INPUT': results['Bad'], 'OVERLAY': outputs['Union_mistakes']['OUTPUT'], 'OUTPUT': parameters['Elsemistake']}
        outputs['Elsemistake'] = processing.run('native:difference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Elsemistake'] = outputs['Elsemistake']['OUTPUT']
        feedback.setCurrentStep(step); step += 1
        if feedback.isCanceled(): return {}

        # Расчет общей площади поля
        total_area_ha = 0.0
        contour_id = results.get('Contourfield')
        if contour_id:
            contour_lyr = context.getMapLayer(contour_id)
            if contour_lyr and contour_lyr.isValid():
                crs = contour_lyr.crs()
                input_lyr = contour_id
                if crs.isGeographic():
                    target_crs = QgsCoordinateReferenceSystem('EPSG:3857')
                    reproj = processing.run('native:reprojectlayer', {
                        'INPUT': input_lyr,
                        'TARGET_CRS': target_crs,
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }, context=context, feedback=feedback, is_child_algorithm=True)
                    input_lyr = reproj['OUTPUT']
                area_res = processing.run('native:fieldcalculator', {
                    'INPUT': input_lyr,
                    'FIELD_NAME': 'area_ha',
                    'FIELD_TYPE': 0, 'FIELD_LENGTH': 12, 'FIELD_PRECISION': 4,
                    'FORMULA': '$area / 10000',
                    'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }, context=context, feedback=feedback, is_child_algorithm=True)
                area_lyr = context.getMapLayer(area_res['OUTPUT'])
                if area_lyr:
                    for f in area_lyr.getFeatures():
                        v = f['area_ha']
                        if isinstance(v, (int, float)):
                            total_area_ha += v

        # Функция для отчета
        def write_stats(layer_id, label, f, total_area):
            if not layer_id:
                f.write(f"{label}: Слой не создан\n")
                return 0.0
            lyr = context.getMapLayer(layer_id)
            if not lyr or not lyr.isValid() or lyr.featureCount() == 0:
                f.write(f"{label}: Слой пуст\n")
                return 0.0
            if 'area_ha' not in [fld.name() for fld in lyr.fields()]:
                f.write(f"{label}: Нет поля 'area_ha'\n")
                return 0.0
            area = 0.0
            count = 0
            for feat in lyr.getFeatures():
                v = feat['area_ha']
                if isinstance(v, (int, float)):
                    area += v
                    count += 1
            pct = (area / total_area * 100) if total_area > 0 else 0.0
            f.write(f"\n{label}:\n")
            f.write(f"  Площадь:  {area:.4f} га\n")
            f.write(f"  Доля:     {pct:.2f}%\n")
            return area

        # Генерация отчета 
        project = QgsProject.instance()
        if project.fileName():
            project_dir = os.path.dirname(project.fileName())
            report_path = os.path.join(project_dir, 'detailed_statistics_report.txt')
        else:
            report_path = os.path.join(QgsProcessingUtils.tempFolder(), 'detailed_statistics_report.txt')
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("ДЕТАЛЬНЫЙ ОТЧЁТ ПО КАЧЕСТВУ ВНЕСЕНИЯ\n")
                f.write("=" * 60 + "\n")
                f.write(f"Общая площадь поля: {total_area_ha:.4f} га\n")
                f.write("-" * 60 + "\n")

                write_stats(results.get('Good'), "Хорошее внесение (95–105%)", f, total_area_ha)
                write_stats(results.get('Under'), "Недовыполнение (<95%)", f, total_area_ha)
                write_stats(results.get('Over'), "Перевыполнение (105–200%)", f, total_area_ha)
                write_stats(results.get('Over2'), "Сильное перевыполнение (>200%)", f, total_area_ha)

                f.write("\n" + "-" * 60 + "\n")
                f.write("Ошибки по локализации:\n")
                write_stats(results.get('Complited_outside'), "Работа \"вне поля\"", f, total_area_ha)
                write_stats(results.get('Transitionmistake'), "Ошибки из-за переходов", f, total_area_ha)
                write_stats(results.get('Contourmistake'), "Ошибки у контура", f, total_area_ha)
                write_stats(results.get('Elsemistake'), "Прочие ошибки", f, total_area_ha)

            feedback.pushInfo(f"Отчёт сохранён: {report_path}")
        except Exception as e:
            feedback.reportError(f"Ошибка записи отчёта: {str(e)}")

        return results

    def name(self) -> str:
        return 'модель'

    def displayName(self) -> str:
        return 'модель'

    def group(self) -> str:
        return ''

    def groupId(self) -> str:
        return ''

    def createInstance(self):
        return self.__class__()
